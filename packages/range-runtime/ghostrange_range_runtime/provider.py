"""The port this package defines for its compute provider.

``packages/vultr-control`` (Agent 02, M2) was an empty directory at the
time this was written — built concurrently, not blocking on it. Rather
than guess at vultr-control's internals, this module defines the small
interface ``RangeRuntimeEngine`` actually needs as a ``Protocol``:
whatever vultr-control ends up looking like, if it exposes something
that structurally satisfies ``ComputeProvider`` (duck-typed — no import
or inheritance required, that's the point of ``Protocol``), it plugs
into the engine with zero changes on this side. See README.md
"Coordination with vultr-control" for the full rationale and the
async-vs-sync caveat.

``get_state`` is intentionally aggregated at (range_id, world_id)
granularity, not per-asset — this package operates at Range/root-World
granularity; per-asset aggregation into one ``ProviderState`` is
vultr-control's job (mirroring PRODUCT.md §3's "all root-World
Assets/Services report healthy" invariant for BOOTING -> READY).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from ghostrange_contracts._base import Id
from ghostrange_contracts.range import RangeSpecV1


class ProviderState(str, Enum):
    """Provider-observed truth for a (range_id, world_id) pair.

    Deliberately a separate vocabulary from ``RangeLifecycleState`` (the
    DB/engine's truth) — reconciliation exists precisely because these
    two can disagree; collapsing them into one enum would make that
    disagreement unrepresentable.
    """

    PROVISIONING = "PROVISIONING"
    BOOTING = "BOOTING"
    READY = "READY"
    FAILED = "FAILED"
    DESTROYING = "DESTROYING"
    DESTROYED = "DESTROYED"
    VANISHED = "VANISHED"
    """The provider has no record of this resource at all, even though
    our own DB expects it to exist in a non-terminal state — e.g. the
    instance was deleted out-of-band. This is the signal
    ``reconcile.py`` uses to mark a Range FAILED rather than assuming
    it's simply still PROVISIONING.
    """

    UNKNOWN = "UNKNOWN"
    """The provider was never asked to provision this (range_id,
    world_id) pair. Distinct from VANISHED (which implies "used to
    exist, or should by now"): UNKNOWN is the honest answer for a pair
    that's still legitimately REQUESTED/PLANNING on the DB side, where
    asking the provider at all is premature.
    """


@dataclass(frozen=True)
class ProviderObservation:
    """One provider-truth snapshot for a (range_id, world_id) pair."""

    state: ProviderState
    detail: str = ""
    resource_ids: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class ComputeProvider(Protocol):
    """The interface ``RangeRuntimeEngine`` drives for the actual
    PROVISIONING/BOOTING/DESTROYING work. ``packages/vultr-control``
    implements this (structurally); ``FakeComputeProvider`` below is the
    deterministic test double every test in this package uses instead.
    """

    def start_provisioning(
        self,
        *,
        range_id: Id,
        world_id: Id,
        spec: RangeSpecV1,
        correlation_id: str,
    ) -> None:
        """Kick off provisioning. Expected to be non-blocking / return
        quickly — progress is observed via repeated ``get_state`` polls,
        matching Vultr's own create-then-poll instance lifecycle (see
        ADR-006) rather than assuming a single synchronous call can
        materialize a whole World.
        """
        ...

    def get_state(self, *, range_id: Id, world_id: Id) -> ProviderObservation:
        """Return the provider's current aggregated truth for this
        (range_id, world_id) pair. Must be safe to call repeatedly
        (idempotent read), including before ``start_provisioning`` was
        ever called (should return ``ProviderState.UNKNOWN`` in that
        case, not raise).
        """
        ...

    def start_destroy(
        self,
        *,
        range_id: Id,
        world_id: Id,
        correlation_id: str,
    ) -> None:
        """Begin tearing down whatever resources exist for this pair,
        including a *partial* set (e.g. some assets provisioned, some
        not, because provisioning failed partway through). Must be safe
        to call on a pair with no resources at all (no-op), since the
        engine's failure-cleanup path calls this unconditionally.
        """
        ...


class FakeComputeProvider:
    """Deterministic, in-memory ``ComputeProvider`` for tests.

    Progress is driven by *call count*, not wall-clock time or sleeps:
    each ``get_state()`` call for a given (range_id, world_id) advances
    an internal step counter, and the returned state is a function of
    that counter versus ``steps_to_ready``/``steps_to_destroyed``. This
    keeps tests fast and exactly reproducible without needing the engine
    to know it's talking to a fake (no special-cased "advance()" call
    from engine code — real polling loops calling ``get_state()``
    repeatedly is exactly what drives this fake forward too).
    """

    def __init__(
        self,
        *,
        steps_to_booting: int = 1,
        steps_to_ready: int = 2,
        steps_to_destroyed: int = 1,
    ) -> None:
        if steps_to_booting < 1:
            raise ValueError("steps_to_booting must be >= 1")
        if steps_to_ready <= steps_to_booting:
            raise ValueError("steps_to_ready must be > steps_to_booting")
        if steps_to_destroyed < 1:
            raise ValueError("steps_to_destroyed must be >= 1")
        self.steps_to_booting = steps_to_booting
        self.steps_to_ready = steps_to_ready
        self.steps_to_destroyed = steps_to_destroyed

        self._provisioned: set[tuple[str, str]] = set()
        self._poll_counts: dict[tuple[str, str], int] = {}
        self._destroy_polls: dict[tuple[str, str], int] = {}
        self._destroying: set[tuple[str, str]] = set()
        self._destroying_resource_ids: dict[tuple[str, str], list[str]] = {}
        self._destroyed: set[tuple[str, str]] = set()
        self._resources: dict[tuple[str, str], list[str]] = {}
        self._fail_at: dict[tuple[str, str], ProviderState] = {}
        self.start_provisioning_calls: list[tuple[str, str, str]] = []
        self.start_destroy_calls: list[tuple[str, str, str]] = []

    @staticmethod
    def _key(range_id: Id, world_id: Id) -> tuple[str, str]:
        return (str(range_id), str(world_id))

    def inject_failure_at(self, range_id: Id, world_id: Id, state: ProviderState) -> None:
        """Test hook: make ``get_state`` report FAILED once the fake's
        internal progression reaches ``state`` (``BOOTING`` or
        ``READY``) for this pair, instead of continuing normally.
        """
        self._fail_at[self._key(range_id, world_id)] = state

    def start_provisioning(
        self,
        *,
        range_id: Id,
        world_id: Id,
        spec: RangeSpecV1,
        correlation_id: str,
    ) -> None:
        key = self._key(range_id, world_id)
        self.start_provisioning_calls.append((*key, correlation_id))
        self._provisioned.add(key)
        self._poll_counts[key] = 0
        self._resources[key] = [f"fake-instance-{asset.id}" for asset in spec.assets] or [
            "fake-instance-default"
        ]

    def get_state(self, *, range_id: Id, world_id: Id) -> ProviderObservation:
        key = self._key(range_id, world_id)

        if key in self._destroyed:
            return ProviderObservation(state=ProviderState.DESTROYED, detail="teardown complete")

        if key in self._destroying:
            self._destroy_polls[key] = self._destroy_polls.get(key, 0) + 1
            if self._destroy_polls[key] >= self.steps_to_destroyed:
                self._destroying.discard(key)
                self._destroyed.add(key)
                self._destroying_resource_ids.pop(key, None)
                return ProviderObservation(state=ProviderState.DESTROYED, detail="teardown complete")
            return ProviderObservation(
                state=ProviderState.DESTROYING,
                detail="teardown in progress",
                resource_ids=tuple(self._destroying_resource_ids.get(key, ())),
            )

        if key not in self._provisioned:
            return ProviderObservation(state=ProviderState.UNKNOWN, detail="never provisioned")

        self._poll_counts[key] = self._poll_counts.get(key, 0) + 1
        count = self._poll_counts[key]
        resources = tuple(self._resources.get(key, ()))
        fail_at = self._fail_at.get(key)

        if count <= self.steps_to_booting:
            return ProviderObservation(state=ProviderState.PROVISIONING, resource_ids=resources)

        if count <= self.steps_to_ready:
            if fail_at == ProviderState.BOOTING:
                return ProviderObservation(
                    state=ProviderState.FAILED,
                    detail="simulated failure during BOOTING",
                    resource_ids=resources,
                )
            return ProviderObservation(state=ProviderState.BOOTING, resource_ids=resources)

        if fail_at == ProviderState.READY:
            return ProviderObservation(
                state=ProviderState.FAILED,
                detail="simulated failure at READY",
                resource_ids=resources,
            )
        return ProviderObservation(state=ProviderState.READY, resource_ids=resources)

    def start_destroy(self, *, range_id: Id, world_id: Id, correlation_id: str) -> None:
        key = self._key(range_id, world_id)
        self.start_destroy_calls.append((*key, correlation_id))
        self._provisioned.discard(key)
        self._destroy_polls[key] = 0
        pending = self._resources.get(key, [])
        # Resources are released from this fake's ledger as soon as
        # teardown is *requested* (matching a real provider where a
        # destroy call is the point past which the resource is no
        # longer billed/owned by us, even if full deletion confirmation
        # takes a few more polls) — see resources_remaining().
        self._resources[key] = []
        if pending:
            self._destroying.add(key)
            self._destroying_resource_ids[key] = pending
        else:
            # Nothing was ever provisioned (or it's already empty) —
            # teardown of an empty resource set completes immediately.
            self._destroyed.add(key)

    def resources_remaining(self, range_id: Id, world_id: Id) -> list[str]:
        return list(self._resources.get(self._key(range_id, world_id), []))


__all__ = [
    "ProviderState",
    "ProviderObservation",
    "ComputeProvider",
    "FakeComputeProvider",
]
