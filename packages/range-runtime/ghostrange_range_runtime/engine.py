"""RangeRuntimeEngine: the actual state machine driver.

Every public method that changes state routes through ``_transition``,
which is the *only* place ``assert_transition`` is called — this is what
guarantees illegal transitions raise (never silently succeed) no matter
which public method triggered the attempt, and that every legal
transition is durably persisted plus published exactly once, in that
order (persist, then publish — mirrors ADR-011's "append happens first"
ordering rationale, applied to this package's own log instead of the
Postgres ``event_log`` it doesn't own).
"""

from __future__ import annotations

import uuid
from typing import Optional

from ghostrange_contracts._base import Id, new_id, utc_now
from ghostrange_contracts.enums import RangeLifecycleState
from ghostrange_contracts.range import RangeSpecV1, RangeV1, assert_transition
from ghostrange_events import WorldDestroyedV1, WorldProvisioningV1, WorldReadyV1, WorldRequestedV1

from .errors import IllegalTransitionError, ValidationFailedError
from .events import EventSink, RangeTransitionEventV1
from .persistence import SqliteTransitionStore
from .provider import ComputeProvider, ProviderState

_TERMINAL = frozenset({RangeLifecycleState.DESTROYED, RangeLifecycleState.FAILED})


def _correlation_id(correlation_id: Optional[str]) -> str:
    return correlation_id or uuid.uuid4().hex


def _validate_spec(spec: RangeSpecV1) -> list[str]:
    """Real (if modest) structural validation for the VALIDATING
    sub-phase — see README gap #1. Returns a list of problems; empty
    means valid.
    """
    problems: list[str] = []
    network_ids = {n.id for n in spec.networks}
    seen_network_ids: set[Id] = set()
    for network in spec.networks:
        if network.id in seen_network_ids:
            problems.append(f"duplicate network id {network.id} ({network.name!r})")
        seen_network_ids.add(network.id)
    for asset in spec.assets:
        if asset.network_id not in network_ids:
            problems.append(
                f"asset {asset.hostname!r} references unknown network_id {asset.network_id}"
            )
    if not spec.assets:
        problems.append("spec declares zero assets — nothing to provision")
    return problems


class RangeRuntimeEngine:
    def __init__(self, store: SqliteTransitionStore, provider: ComputeProvider, sink: EventSink) -> None:
        self.store = store
        self.provider = provider
        self.sink = sink
        # Cache of the spec each Range was validated against, keyed by
        # range_id — only used to fill in asset/network counts on the
        # root-World WorldReadyV1 event (see _maybe_emit_root_world_event).
        # Not durable and not authoritative state; RangeSpecV1 itself is
        # immutable/content-addressed (Decisions.md/PRODUCT.md §2.1) so
        # re-populating this from storage on restart, if ever needed, is
        # a lookup by range_record.spec_id, not a new concern.
        self._spec_cache: dict[Id, RangeSpecV1] = {}
        # Who asked for this Range (for the root World's WorldRequestedV1
        # event's requested_by field) — set in create_range.
        self._requested_by: dict[Id, str] = {}

    # -- restart / resume -------------------------------------------------

    def load_range(self, range_id: Id) -> Optional[RangeV1]:
        """Reload a Range's current record after a process restart. The
        snapshot cache is the fast path; if it's ever missing but the
        transition log has rows (shouldn't happen since both are
        written together, but this is the honest fallback), at least
        the current *state* can be recovered from the log even though
        the rest of the record can't be reconstructed — callers should
        treat that case as needing manual recovery, which is why this
        returns ``None`` rather than fabricating a record.
        """
        return self.store.load_snapshot(range_id)

    # -- internal: the one place transitions actually happen ---------------

    def _transition(
        self,
        range_record: RangeV1,
        target: RangeLifecycleState,
        reason: str,
        correlation_id: str,
    ) -> RangeV1:
        current = range_record.status
        try:
            assert_transition(current, target)
        except ValueError as exc:
            raise IllegalTransitionError(range_record.id, current, target, str(exc)) from exc

        now = utc_now()
        range_record.status = target
        range_record.updated_at = now
        if target == RangeLifecycleState.DESTROYED:
            range_record.destroyed_at = now
        if target == RangeLifecycleState.FAILED:
            range_record.failure_reason = range_record.failure_reason or reason

        self.store.append(
            range_id=range_record.id,
            world_id=range_record.root_world_id,
            previous_state=current,
            new_state=target,
            reason=reason,
            correlation_id=correlation_id,
            timestamp=now,
        )
        self.store.save_snapshot(range_record)

        self.sink.publish(
            RangeTransitionEventV1(
                range_id=range_record.id,
                world_id=range_record.root_world_id,
                previous_state=current,
                new_state=target,
                reason=reason,
                correlation_id=correlation_id,
                occurred_at=now,
            )
        )
        self._maybe_emit_root_world_event(range_record, current, target, correlation_id)
        return range_record

    def _checkpoint(self, range_record: RangeV1, note: str, correlation_id: str) -> RangeV1:
        """Durable, no-op (state unchanged) milestone note — does NOT go
        through ``assert_transition`` since nothing is transitioning.
        Used for the AUTHORIZED sub-phase inside PLANNING; see README
        gap #1.
        """
        now = utc_now()
        current = range_record.status
        self.store.append(
            range_id=range_record.id,
            world_id=range_record.root_world_id,
            previous_state=current,
            new_state=current,
            reason=note,
            correlation_id=correlation_id,
            timestamp=now,
        )
        self.store.save_snapshot(range_record)
        self.sink.publish(
            RangeTransitionEventV1(
                range_id=range_record.id,
                world_id=range_record.root_world_id,
                previous_state=current,
                new_state=current,
                reason=note,
                correlation_id=correlation_id,
                occurred_at=now,
            )
        )
        return range_record

    def _maybe_emit_root_world_event(
        self,
        range_record: RangeV1,
        previous: RangeLifecycleState,
        target: RangeLifecycleState,
        correlation_id: str,
    ) -> None:
        """Emit a real ``ghostrange_events`` World payload for the root
        World where one already fits (see README gap #3) — this
        package treats itself as also owning root-World lifecycle
        advancement (PRODUCT.md §4).
        """
        if range_record.root_world_id is None:
            return
        world_id = range_record.root_world_id
        range_id = range_record.id

        if previous == RangeLifecycleState.REQUESTED and target == RangeLifecycleState.PLANNING:
            self.sink.publish(
                WorldRequestedV1(
                    world_id=world_id,
                    range_id=range_id,
                    parent_world_id=None,
                    requested_by=self._requested_by.get(range_id, "unknown"),
                )
            )
        elif previous == RangeLifecycleState.PLANNING and target == RangeLifecycleState.PROVISIONING:
            self.sink.publish(WorldProvisioningV1(world_id=world_id, range_id=range_id))
        elif previous == RangeLifecycleState.BOOTING and target == RangeLifecycleState.READY:
            spec = self._spec_cache.get(range_id)
            self.sink.publish(
                WorldReadyV1(
                    world_id=world_id,
                    range_id=range_id,
                    asset_count=len(spec.assets) if spec else 0,
                    network_count=len(spec.networks) if spec else 0,
                )
            )
        elif previous == RangeLifecycleState.DESTROYING and target == RangeLifecycleState.DESTROYED:
            self.sink.publish(WorldDestroyedV1(world_id=world_id, range_id=range_id, reason=None))
        # EXECUTING / VERIFYING / STOPPING / FAILED have no WorldStatus-
        # backed event today (README gap #3) — RangeTransitionEventV1
        # (already published by _transition) is the only signal for
        # those until packages/events grows one.

    # -- REQUESTED -> PLANNING (VALIDATING + AUTHORIZED sub-phases) -------

    def create_range(
        self, spec: RangeSpecV1, *, requested_by: str, correlation_id: Optional[str] = None
    ) -> RangeV1:
        correlation_id = _correlation_id(correlation_id)
        now = utc_now()
        range_record = RangeV1(
            spec_id=spec.id,
            spec_version=spec.schema_version,
            status=RangeLifecycleState.REQUESTED,
            created_at=now,
            updated_at=now,
        )
        self._requested_by[range_record.id] = requested_by
        # Creation-from-nothing is itself durably recorded, with
        # previous_state=None, so a restart can tell "this range was
        # created at all" apart from "no record exists."
        self.store.append(
            range_id=range_record.id,
            world_id=None,
            previous_state=None,
            new_state=RangeLifecycleState.REQUESTED,
            reason=f"range requested by {requested_by}",
            correlation_id=correlation_id,
            timestamp=now,
        )
        self.store.save_snapshot(range_record)
        self.sink.publish(
            RangeTransitionEventV1(
                range_id=range_record.id,
                world_id=None,
                previous_state=None,
                new_state=RangeLifecycleState.REQUESTED,
                reason=f"range requested by {requested_by}",
                correlation_id=correlation_id,
                occurred_at=now,
            )
        )
        return range_record

    def validate_and_authorize(
        self,
        range_record: RangeV1,
        spec: RangeSpecV1,
        *,
        policy_attached: bool = True,
        budget_attached: bool = True,
        correlation_id: Optional[str] = None,
    ) -> RangeV1:
        correlation_id = _correlation_id(correlation_id)

        # --- VALIDATING sub-phase ---
        problems = _validate_spec(spec)
        if problems:
            detail = "; ".join(problems)
            range_record = self._transition(
                range_record,
                RangeLifecycleState.FAILED,
                reason=f"VALIDATING failed: {detail}",
                correlation_id=correlation_id,
            )
            raise ValidationFailedError(f"RangeSpec {spec.id} failed validation: {detail}")

        range_record.root_world_id = new_id()
        range_record.world_ids = [range_record.root_world_id]
        self._spec_cache[range_record.id] = spec
        range_record = self._transition(
            range_record,
            RangeLifecycleState.PLANNING,
            reason="VALIDATING passed: spec well-formed, root World allocated",
            correlation_id=correlation_id,
        )

        # --- AUTHORIZED sub-phase (checkpoint, no state change — gap #1) ---
        if not (policy_attached and budget_attached):
            missing = []
            if not policy_attached:
                missing.append("policy")
            if not budget_attached:
                missing.append("budget")
            range_record = self._transition(
                range_record,
                RangeLifecycleState.FAILED,
                reason=f"AUTHORIZED failed: missing {', '.join(missing)} attachment",
                correlation_id=correlation_id,
            )
            raise ValidationFailedError(
                f"Range {range_record.id} not authorized: missing {', '.join(missing)}"
            )

        range_record = self._checkpoint(
            range_record,
            note="AUTHORIZED: policy and budget attached",
            correlation_id=correlation_id,
        )
        return range_record

    # -- PLANNING -> PROVISIONING -> BOOTING -> READY ----------------------

    def provision(
        self, range_record: RangeV1, spec: RangeSpecV1, *, correlation_id: Optional[str] = None
    ) -> RangeV1:
        correlation_id = _correlation_id(correlation_id)
        range_record = self._transition(
            range_record,
            RangeLifecycleState.PROVISIONING,
            reason="beginning provisioning via compute provider",
            correlation_id=correlation_id,
        )
        try:
            self.provider.start_provisioning(
                range_id=range_record.id,
                world_id=range_record.root_world_id,
                spec=spec,
                correlation_id=correlation_id,
            )
        except Exception as exc:  # noqa: BLE001 - provider errors are provider-defined
            self._cleanup_and_fail(
                range_record,
                reason=f"provider raised during start_provisioning: {exc}",
                correlation_id=correlation_id,
            )
        return range_record

    def run_provisioning_to_ready(
        self, range_record: RangeV1, *, correlation_id: Optional[str] = None, max_polls: int = 50
    ) -> RangeV1:
        """Poll ``provider.get_state`` and walk the *legal* intermediate
        transitions until READY or FAILED. Never jumps straight from
        PROVISIONING to READY even if the provider already reports
        READY on the first poll — BOOTING is always visited, still
        durably recorded, still checked by ``assert_transition``.
        """
        correlation_id = _correlation_id(correlation_id)
        for _ in range(max_polls):
            if range_record.status in _TERMINAL:
                return range_record
            obs = self.provider.get_state(range_id=range_record.id, world_id=range_record.root_world_id)

            if obs.state == ProviderState.FAILED:
                self._cleanup_and_fail(
                    range_record,
                    reason=f"provisioning failed: {obs.detail or 'provider reported FAILED'}",
                    correlation_id=correlation_id,
                )
                return range_record

            if obs.state in (ProviderState.PROVISIONING, ProviderState.UNKNOWN):
                continue

            if obs.state in (ProviderState.BOOTING, ProviderState.READY):
                if range_record.status == RangeLifecycleState.PROVISIONING:
                    range_record = self._transition(
                        range_record,
                        RangeLifecycleState.BOOTING,
                        reason=f"provider reports {obs.state.value}",
                        correlation_id=correlation_id,
                    )
                if obs.state == ProviderState.READY and range_record.status == RangeLifecycleState.BOOTING:
                    range_record = self._transition(
                        range_record,
                        RangeLifecycleState.READY,
                        reason="provider reports READY: all root-World assets healthy",
                        correlation_id=correlation_id,
                    )
                    return range_record
        raise TimeoutError(
            f"Range {range_record.id} did not reach READY/FAILED within {max_polls} provider polls"
        )

    def _cleanup_and_fail(self, range_record: RangeV1, *, reason: str, correlation_id: str) -> RangeV1:
        """Best-effort partial-resource cleanup, then FAILED. Cleanup is
        attempted even if it itself raises — a failed cleanup call must
        never prevent the Range from reaching FAILED (that would leave
        the Range stuck, which is worse).
        """
        try:
            self.provider.start_destroy(
                range_id=range_record.id,
                world_id=range_record.root_world_id,
                correlation_id=correlation_id,
            )
            cleanup_note = "partial-resource cleanup triggered"
        except Exception as cleanup_exc:  # noqa: BLE001
            cleanup_note = f"partial-resource cleanup ALSO failed: {cleanup_exc}"
        return self._transition(
            range_record,
            RangeLifecycleState.FAILED,
            reason=f"{reason}; {cleanup_note}",
            correlation_id=correlation_id,
        )

    # -- READY <-> EXECUTING <-> VERIFYING ---------------------------------

    def start_execution(self, range_record: RangeV1, *, correlation_id: Optional[str] = None) -> RangeV1:
        return self._transition(
            range_record,
            RangeLifecycleState.EXECUTING,
            reason="first Task dispatched against the root World",
            correlation_id=_correlation_id(correlation_id),
        )

    def start_verifying(
        self, range_record: RangeV1, *, reason: str = "verification requested", correlation_id: Optional[str] = None
    ) -> RangeV1:
        return self._transition(
            range_record,
            RangeLifecycleState.VERIFYING,
            reason=reason,
            correlation_id=_correlation_id(correlation_id),
        )

    def resume_execution(
        self,
        range_record: RangeV1,
        *,
        reason: str = "verification failure spawned further remediation work",
        correlation_id: Optional[str] = None,
    ) -> RangeV1:
        return self._transition(
            range_record,
            RangeLifecycleState.EXECUTING,
            reason=reason,
            correlation_id=_correlation_id(correlation_id),
        )

    # -- STOPPING -> DESTROYING -> DESTROYED --------------------------------

    def stop(
        self, range_record: RangeV1, *, reason: str, correlation_id: Optional[str] = None
    ) -> RangeV1:
        return self._transition(
            range_record,
            RangeLifecycleState.STOPPING,
            reason=reason,
            correlation_id=_correlation_id(correlation_id),
        )

    def begin_destroy(self, range_record: RangeV1, *, correlation_id: Optional[str] = None) -> RangeV1:
        correlation_id = _correlation_id(correlation_id)
        range_record = self._transition(
            range_record,
            RangeLifecycleState.DESTROYING,
            reason="evidence/artifact export confirmed complete, tearing down",
            correlation_id=correlation_id,
        )
        self.provider.start_destroy(
            range_id=range_record.id,
            world_id=range_record.root_world_id,
            correlation_id=correlation_id,
        )
        return range_record

    def run_teardown_to_destroyed(
        self, range_record: RangeV1, *, correlation_id: Optional[str] = None, max_polls: int = 50
    ) -> RangeV1:
        correlation_id = _correlation_id(correlation_id)
        for _ in range(max_polls):
            if range_record.status in _TERMINAL:
                return range_record
            obs = self.provider.get_state(range_id=range_record.id, world_id=range_record.root_world_id)
            if obs.state == ProviderState.DESTROYED:
                return self._transition(
                    range_record,
                    RangeLifecycleState.DESTROYED,
                    reason="all Assets/ComputeWorkers under the Range confirmed torn down",
                    correlation_id=correlation_id,
                )
        raise TimeoutError(
            f"Range {range_record.id} did not reach DESTROYED within {max_polls} provider polls"
        )

    # -- FAILED (from anywhere) --------------------------------------------

    def fail(
        self,
        range_record: RangeV1,
        *,
        reason: str,
        correlation_id: Optional[str] = None,
        cleanup: bool = True,
    ) -> RangeV1:
        correlation_id = _correlation_id(correlation_id)
        if cleanup:
            return self._cleanup_and_fail(range_record, reason=reason, correlation_id=correlation_id)
        return self._transition(
            range_record, RangeLifecycleState.FAILED, reason=reason, correlation_id=correlation_id
        )


__all__ = ["RangeRuntimeEngine"]
