"""The "registry DB" EXECUTION_POLICY.md §1/§3.2 names as policy-check's
source of truth: canonical target sets per range, the reviewed ability
catalog, per-world quota counters, and human-approval records.

This is an in-memory, process-local M2 stub. A real deployment persists
this in Postgres with the append-only grant discipline described in
EXECUTION_POLICY.md §8/§4 (mTLS-only, no agent-reachable admin surface).
The stub exists so ``authorize()``'s re-derivation step (§3.2 step 2: "never
trust the request's own claims about its own authorization") has a real,
independently-populated source to re-derive from, and so this package's own
tests exercise the actual security property instead of mocking it away.

Mutating methods here (``register_range``, ``register_ability``,
``set_quota``, ``record_approval``) stand in for what, in production, only
range-runtime's provisioning pipeline and the human-approval endpoint are
allowed to call. Nothing on this class is reachable from anything an agent
can say (Decisions.md #9) — it is plain Python call surface used by
range-runtime and a human-approval endpoint, never proxied through the
orchestrator's own agent-facing API.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from ghostrange_contracts._base import Id
from ghostrange_contracts.enums import AbilityCategory
from ghostrange_contracts.policy import TargetRef


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UnknownRangeError(Exception):
    """Raised when a request/token references a range_id policy-check has
    no registry entry for. This is a fail-closed condition, not "assume
    empty target set and deny gracefully further down" — an unknown range
    must never be silently treated as "no targets, but otherwise fine."
    """


@dataclass
class Approval:
    request_hash: str
    approver: str
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return _utc_now() >= self.expires_at


class PolicyRegistry:
    """In-memory registry: one instance per policy-check process/test.

    Thread-safety: a single lock guards all mutation. This is a stub-level
    concern (real deployment: Postgres transactions), included so the
    class is at least safe to use from concurrent tests/callers without
    corrupting quota counters.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._target_sets: dict[Id, list[TargetRef]] = {}
        self._target_aliases: dict[Id, dict[str, TargetRef]] = {}
        self._ability_catalog: set[str] = set()
        self._quota_ceiling: dict[Id, float] = {}
        self._quota_spent: dict[Id, float] = {}
        self._approvals: dict[str, Approval] = {}
        self.human_approval_required_categories: set[AbilityCategory] = set()

    # -- range provisioning (range-runtime only, conceptually) ------------

    def register_range(
        self,
        range_id: Id,
        target_set: list[TargetRef],
        *,
        target_aliases: Optional[dict[str, TargetRef]] = None,
    ) -> None:
        """Record the canonical, just-provisioned target set for a range.

        ``target_aliases`` is the pre-declared, model-facing vocabulary
        (see ``model_output_guard.py``): a mapping from an opaque alias a
        DAG node exposes to the agent (e.g. ``"target-0"``) to the real
        ``TargetRef``. If omitted, sequential aliases are generated —
        convenient for tests, but a real execution-graph compiler should
        supply its own stable aliases at DAG-compile time.
        """
        with self._lock:
            self._target_sets[range_id] = list(target_set)
            if target_aliases is None:
                target_aliases = {f"target-{i}": t for i, t in enumerate(target_set)}
            self._target_aliases[range_id] = dict(target_aliases)

    def deregister_range(self, range_id: Id) -> None:
        """Called at teardown (EXECUTION_POLICY.md §9) — after this, any
        request naming this range_id fails closed with UnknownRangeError,
        same as a range that was never provisioned.
        """
        with self._lock:
            self._target_sets.pop(range_id, None)
            self._target_aliases.pop(range_id, None)

    def get_target_set(self, range_id: Id) -> list[TargetRef]:
        try:
            return list(self._target_sets[range_id])
        except KeyError:
            raise UnknownRangeError(str(range_id)) from None

    def get_target_aliases(self, range_id: Id) -> dict[str, TargetRef]:
        try:
            return dict(self._target_aliases[range_id])
        except KeyError:
            raise UnknownRangeError(str(range_id)) from None

    # -- ability catalog (T11: reviewed abilities only) -------------------

    def register_ability(self, ability_ref: str) -> None:
        with self._lock:
            self._ability_catalog.add(ability_ref)

    def is_reviewed_ability(self, ability_ref: str) -> bool:
        return ability_ref in self._ability_catalog

    # -- quotas (T13) -------------------------------------------------------

    def set_quota(self, world_id: Id, max_cost: float) -> None:
        with self._lock:
            self._quota_ceiling[world_id] = max_cost
            self._quota_spent.setdefault(world_id, 0.0)

    def admit_quota(self, world_id: Id, cost: float) -> bool:
        """Fail closed: a world with no registered quota has NOT been
        provisioned with an admission budget and is denied by default,
        the same way an unknown range is denied rather than treated as
        "no targets registered yet, so anything goes."
        """
        with self._lock:
            ceiling = self._quota_ceiling.get(world_id)
            if ceiling is None:
                return False
            spent = self._quota_spent.get(world_id, 0.0)
            if spent + cost > ceiling:
                return False
            self._quota_spent[world_id] = spent + cost
            return True

    # -- human approval (T15, §7) ------------------------------------------

    def record_approval(self, request_hash: str, approver: str, ttl: timedelta) -> None:
        with self._lock:
            self._approvals[request_hash] = Approval(
                request_hash=request_hash, approver=approver, expires_at=_utc_now() + ttl
            )

    def get_approval(self, request_hash: str) -> Optional[Approval]:
        return self._approvals.get(request_hash)


__all__ = ["PolicyRegistry", "UnknownRangeError", "Approval"]
