"""Reconciliation: DB truth vs. provider truth.

The engine's own transitions keep the DB (``SqliteTransitionStore``) and
the provider roughly in step by construction (poll, then transition), but
nothing here assumes that stays true forever: a process crash mid-poll, a
provider-side change that happened out of band, or simply two processes
racing can all leave the DB's remembered state stale relative to what the
provider will now report. ``Reconciler`` is the sketch (per the brief:
"even if not fully wired to a real provider yet") of the loop that closes
that gap.

Design: DB says X, provider says Y ->
  - if X == Y (after mapping the provider's vocabulary onto
    ``RangeLifecycleState``): nothing to do.
  - if Y is *forward* of X along a legal path in
    ``RANGE_LIFECYCLE_TRANSITIONS``: walk that path one legal transition
    at a time (never jump straight to Y), so every hop is still durably
    recorded and still checked by ``assert_transition``.
  - if the provider reports the resource is simply gone
    (``ProviderState.VANISHED``) while the DB expects it to still exist:
    mark the Range FAILED, with a reason that says exactly that.
  - if Y is *behind* X, or otherwise unreachable from X by any legal
    path (an anomaly — e.g. the DB thinks a Range is EXECUTING, which is
    a range-runtime-internal phase the provider was never asked about,
    yet the provider reports PROVISIONING): do **not** guess a
    correction. Report it as an anomaly for a human/operator to look at,
    rather than silently mutating state in a direction the state machine
    doesn't actually license.
  - terminal Ranges (DESTROYED/FAILED) are always a no-op — a dead Range
    does not reanimate no matter what the provider says.

**What is not wired up here** (explicitly, per the brief's "sketch, even
if not fully wired to a real provider yet"): a scheduler that calls
``reconcile_all`` on an interval inside a long-running process. That's an
infra/ownership decision (``apps/api``? a standalone worker?) outside
this package's scope — see README "Reconciliation".
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ghostrange_contracts._base import Id
from ghostrange_contracts.enums import RangeLifecycleState
from ghostrange_contracts.range import RANGE_LIFECYCLE_TRANSITIONS, RangeV1

from .engine import RangeRuntimeEngine, _correlation_id
from .provider import ProviderState

_TERMINAL = frozenset({RangeLifecycleState.DESTROYED, RangeLifecycleState.FAILED})

# Only these ProviderStates have a direct RangeLifecycleState analogue.
# EXECUTING/VERIFYING/STOPPING/PLANNING/REQUESTED are range-runtime-
# internal phases the provider is never asked about, so there is
# deliberately no entry for them here — see reconcile_one's handling of
# obs.state in (UNKNOWN,) below.
_PROVIDER_TO_RANGE_STATE: dict[ProviderState, RangeLifecycleState] = {
    ProviderState.PROVISIONING: RangeLifecycleState.PROVISIONING,
    ProviderState.BOOTING: RangeLifecycleState.BOOTING,
    ProviderState.READY: RangeLifecycleState.READY,
    ProviderState.DESTROYING: RangeLifecycleState.DESTROYING,
    ProviderState.DESTROYED: RangeLifecycleState.DESTROYED,
}


class ReconcileAction(str, Enum):
    NO_OP = "NO_OP"
    ADVANCED = "ADVANCED"
    MARKED_FAILED = "MARKED_FAILED"
    SKIPPED_TERMINAL = "SKIPPED_TERMINAL"
    SKIPPED_NOT_YET_PROVISIONED = "SKIPPED_NOT_YET_PROVISIONED"
    ANOMALY = "ANOMALY"


@dataclass
class ReconcileOutcome:
    range_id: Id
    action: ReconcileAction
    detail: str
    range_record: Optional[RangeV1] = None


def _shortest_legal_path(
    current: RangeLifecycleState, target: RangeLifecycleState
) -> Optional[list[RangeLifecycleState]]:
    """BFS over ``RANGE_LIFECYCLE_TRANSITIONS`` for the shortest sequence
    of legal hops from ``current`` to ``target`` (exclusive of
    ``current``, inclusive of ``target``). Returns ``None`` if no such
    forward path exists (target is unreachable, e.g. behind current).
    """
    if current == target:
        return []
    frontier: deque[tuple[RangeLifecycleState, list[RangeLifecycleState]]] = deque(
        [(current, [])]
    )
    visited = {current}
    while frontier:
        state, path = frontier.popleft()
        for nxt in RANGE_LIFECYCLE_TRANSITIONS.get(state, frozenset()):
            if nxt in visited:
                continue
            new_path = path + [nxt]
            if nxt == target:
                return new_path
            visited.add(nxt)
            frontier.append((nxt, new_path))
    return None


class Reconciler:
    def __init__(self, engine: RangeRuntimeEngine) -> None:
        self.engine = engine

    def reconcile_one(
        self, range_record: RangeV1, *, correlation_id: Optional[str] = None
    ) -> ReconcileOutcome:
        correlation_id = _correlation_id(correlation_id)
        db_state = range_record.status

        if db_state in _TERMINAL:
            return ReconcileOutcome(
                range_id=range_record.id,
                action=ReconcileAction.SKIPPED_TERMINAL,
                detail=f"Range is terminal ({db_state.value}); provider truth not consulted",
                range_record=range_record,
            )

        if range_record.root_world_id is None:
            return ReconcileOutcome(
                range_id=range_record.id,
                action=ReconcileAction.SKIPPED_NOT_YET_PROVISIONED,
                detail="root World not yet allocated (Range still REQUESTED) — nothing to check",
                range_record=range_record,
            )

        obs = self.engine.provider.get_state(
            range_id=range_record.id, world_id=range_record.root_world_id
        )

        if obs.state == ProviderState.VANISHED:
            updated = self.engine.fail(
                range_record,
                reason=(
                    f"reconciliation: provider reports resource VANISHED while DB "
                    f"expected {db_state.value} — resource disappeared out of band"
                ),
                correlation_id=correlation_id,
                cleanup=False,
            )
            return ReconcileOutcome(
                range_id=range_record.id,
                action=ReconcileAction.MARKED_FAILED,
                detail="provider truth: resource vanished unexpectedly",
                range_record=updated,
            )

        if obs.state == ProviderState.FAILED:
            self.engine._cleanup_and_fail(  # noqa: SLF001 - reconciler is engine-internal collaborator
                range_record,
                reason=f"reconciliation: provider reports FAILED ({obs.detail})",
                correlation_id=correlation_id,
            )
            return ReconcileOutcome(
                range_id=range_record.id,
                action=ReconcileAction.MARKED_FAILED,
                detail="provider truth: FAILED",
                range_record=range_record,
            )

        target_state = _PROVIDER_TO_RANGE_STATE.get(obs.state)
        if target_state is None:
            # UNKNOWN, or a provider vocabulary member we don't have an
            # opinion about yet — nothing safe to do.
            return ReconcileOutcome(
                range_id=range_record.id,
                action=ReconcileAction.NO_OP,
                detail=f"provider reports {obs.state.value}; no mapped Range state to reconcile against",
                range_record=range_record,
            )

        if db_state == target_state:
            return ReconcileOutcome(
                range_id=range_record.id,
                action=ReconcileAction.NO_OP,
                detail=f"DB and provider agree: {db_state.value}",
                range_record=range_record,
            )

        path = _shortest_legal_path(db_state, target_state)
        if path is None:
            return ReconcileOutcome(
                range_id=range_record.id,
                action=ReconcileAction.ANOMALY,
                detail=(
                    f"DB says {db_state.value}, provider says {target_state.value} "
                    "(via observed provider state "
                    f"{obs.state.value}), and no legal forward path connects them — "
                    "not correcting automatically, needs operator review"
                ),
                range_record=range_record,
            )

        for hop in path:
            range_record = self.engine._transition(  # noqa: SLF001
                range_record,
                hop,
                reason=f"reconciliation: provider observed {obs.state.value}, catching up DB",
                correlation_id=correlation_id,
            )
        return ReconcileOutcome(
            range_id=range_record.id,
            action=ReconcileAction.ADVANCED,
            detail=f"DB advanced {db_state.value} -> {' -> '.join(s.value for s in path)}",
            range_record=range_record,
        )

    def reconcile_all(
        self, range_records: list[RangeV1], *, correlation_id: Optional[str] = None
    ) -> list[ReconcileOutcome]:
        """Reconcile a batch of Ranges (e.g. every non-terminal Range the
        store knows about). Callers are responsible for loading the
        records (typically via ``engine.store.all_range_ids`` +
        ``engine.load_range``) and for deciding how often this runs —
        see the module docstring's "what is not wired up here."
        """
        return [
            self.reconcile_one(record, correlation_id=correlation_id) for record in range_records
        ]


__all__ = ["Reconciler", "ReconcileOutcome", "ReconcileAction"]
