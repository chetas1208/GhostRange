"""Adapter: ``ghostrange_vultr_control.VultrControlProvider`` -> this
package's ``ComputeProvider`` port.

When this package was started, ``packages/vultr-control`` was an empty
directory (Agent 02's work was concurrent, per M2_COORDINATION.md — see
``provider.py``'s docstring and README "Coordination with vultr-control").
It has since landed a real, well-specified interface
(``ghostrange_vultr_control.interface.VultrControlProvider``) that its own
README states ``packages/range-runtime`` is built against. This module is
that integration: a real (not hypothetical) implementation of
``ComputeProvider`` that drives ``VultrControlProvider`` — so
``RangeRuntimeEngine`` can be constructed with
``VultrAdaptedComputeProvider(MockVultrProvider())`` for a fully-real,
two-package integration test (see
``tests/test_vultr_adapter.py``), or
``VultrAdaptedComputeProvider(RealVultrProvider())`` once live Vultr
credentials are available — no engine changes needed either way.

Granularity mismatch, resolved here: ``ComputeProvider`` (this package)
operates at Range/root-World granularity (one aggregated
``ProviderState``); ``VultrControlProvider`` operates per-resource (one
VPC "world" + N compute instances). This adapter is the aggregation glue
— exactly the translation both packages' docs point at each other to do.
See "Gap found" below for the one real limitation this surfaced.

Teardown ordering follows ``VultrControlProvider.destroy_world``'s own
documented contract ("callers should destroy every compute attached to
this world *before* calling this — a provider implementation is not
required to cascade-delete attached instances"): every compute is
destroyed first, then the world.

Gap found (report, not silently worked around): ``VultrControlProvider``
only exposes ``ResourceStatus`` = PENDING/ACTIVE/DELETING/DELETED/ERROR —
there is no signal between "Vultr's API reports the instance active" and
"cloud-init has actually finished configuring the OS" (this is explicit
in ``wait_until_ready``'s own docstring: "it does NOT mean cloud-init has
finished... Callers that need that finer signal must probe it
themselves"). This adapter therefore cannot distinguish
``ProviderState.PROVISIONING`` from ``ProviderState.BOOTING`` using this
interface alone — it reports ``READY`` as soon as every compute is
``ACTIVE``. This is not a correctness bug in ``RangeRuntimeEngine``:
``run_provisioning_to_ready`` (see ``engine.py``) always walks the
``PROVISIONING -> BOOTING -> READY`` hop explicitly regardless of what
the provider reports (it never skips BOOTING even when the provider
jumps straight to READY), so the Range's own persisted lifecycle is
still correct and complete — only the *provider-truth* signal is
coarser than the Range lifecycle's granularity. Closing this properly
would need either an application-level health check
(``packages/execution-graph``/whatever probes the asset once it's
believed ready) or a future ``VultrControlProvider`` addition; flagging
for Agent 02/01 rather than guessing at cloud-init-done detection here.
"""

from __future__ import annotations

from typing import Optional

from ghostrange_contracts._base import Id
from ghostrange_contracts.range import RangeSpecV1
from ghostrange_vultr_control import (
    ComputeRecord,
    CreateComputeRequest,
    CreateWorldRequest,
    GhostRangeTags,
    ResourceStatus,
)
from ghostrange_vultr_control.errors import VultrControlError, VultrNotFoundError
from ghostrange_vultr_control.interface import VultrControlProvider

from .provider import ProviderObservation, ProviderState


def _key(range_id: Id, world_id: Id) -> tuple[str, str]:
    return (str(range_id), str(world_id))


class VultrAdaptedComputeProvider:
    """Real ``ComputeProvider`` implementation, backed by any
    ``VultrControlProvider`` (``MockVultrProvider`` for tests/offline dev,
    ``RealVultrProvider`` for live Vultr — both satisfy the same ABC).
    """

    def __init__(
        self,
        vultr: VultrControlProvider,
        *,
        region: str = "ewr",
        plan: str = "vc2-1c-1gb",
        os_id: int = 1743,
    ) -> None:
        self._vultr = vultr
        self._region = region
        self._plan = plan
        self._os_id = os_id

        self._world_refs: dict[tuple[str, str], str] = {}
        self._compute_refs: dict[tuple[str, str], list[str]] = {}
        self._failed_detail: dict[tuple[str, str], str] = {}
        self._destroying: set[tuple[str, str]] = set()
        self._destroyed: set[tuple[str, str]] = set()

    def start_provisioning(
        self,
        *,
        range_id: Id,
        world_id: Id,
        spec: RangeSpecV1,
        correlation_id: str,
    ) -> None:
        key = _key(range_id, world_id)
        tags = GhostRangeTags(range_id=str(range_id), world_id=str(world_id))
        try:
            world_record = self._vultr.create_world(
                CreateWorldRequest(region=self._region, tags=tags)
            )
        except VultrControlError as exc:
            self._failed_detail[key] = f"create_world failed: {exc}"
            return

        self._world_refs[key] = world_record.provider_world_id
        compute_ids: list[str] = []
        for asset in spec.assets:
            try:
                record = self._vultr.create_compute(
                    CreateComputeRequest(
                        world_ref=world_record.provider_world_id,
                        region=self._region,
                        plan=self._plan,
                        os_id=self._os_id,
                        tags=tags,
                        hostname=asset.hostname,
                        label=f"{asset.hostname}-{world_id}",
                    )
                )
            except VultrControlError as exc:
                self._compute_refs[key] = compute_ids
                self._failed_detail[key] = (
                    f"create_compute failed for asset {asset.hostname!r}: {exc}"
                )
                return
            compute_ids.append(record.provider_compute_id)
        self._compute_refs[key] = compute_ids

    def get_state(self, *, range_id: Id, world_id: Id) -> ProviderObservation:
        key = _key(range_id, world_id)

        if key in self._destroyed:
            return ProviderObservation(state=ProviderState.DESTROYED)
        if key in self._destroying:
            return ProviderObservation(
                state=ProviderState.DESTROYING, detail=self._failed_detail.get(key, "")
            )
        if key in self._failed_detail:
            return ProviderObservation(state=ProviderState.FAILED, detail=self._failed_detail[key])
        if key not in self._world_refs:
            return ProviderObservation(state=ProviderState.UNKNOWN)

        compute_ids = self._compute_refs.get(key, [])
        if not compute_ids:
            return ProviderObservation(state=ProviderState.PROVISIONING, detail="world created, no compute yet")

        records: list[ComputeRecord] = []
        for compute_id in compute_ids:
            try:
                records.append(self._vultr.get_compute(compute_id))
            except VultrNotFoundError:
                return ProviderObservation(
                    state=ProviderState.VANISHED,
                    detail=f"compute {compute_id} no longer exists on the provider",
                    resource_ids=tuple(compute_ids),
                )

        if any(r.status == ResourceStatus.ERROR for r in records):
            return ProviderObservation(
                state=ProviderState.FAILED,
                detail="one or more compute instances reported ERROR",
                resource_ids=tuple(compute_ids),
            )
        if all(r.status == ResourceStatus.ACTIVE for r in records):
            # See module docstring "Gap found": VultrControlProvider has
            # no cloud-init-done signal, so ACTIVE maps straight to READY
            # here — engine.run_provisioning_to_ready still walks the
            # BOOTING hop regardless.
            return ProviderObservation(state=ProviderState.READY, resource_ids=tuple(compute_ids))
        return ProviderObservation(state=ProviderState.PROVISIONING, resource_ids=tuple(compute_ids))

    def start_destroy(self, *, range_id: Id, world_id: Id, correlation_id: str) -> None:
        key = _key(range_id, world_id)
        if key in self._destroyed:
            return
        self._destroying.add(key)
        errors: list[str] = []

        for compute_id in self._compute_refs.get(key, []):
            try:
                self._vultr.destroy_compute(compute_id)
            except VultrNotFoundError:
                pass  # already gone — teardown's goal state, not a failure
            except VultrControlError as exc:
                errors.append(f"destroy_compute({compute_id}) failed: {exc}")
        self._compute_refs[key] = []

        world_ref = self._world_refs.get(key)
        if world_ref is not None:
            try:
                self._vultr.destroy_world(world_ref)
                self._world_refs.pop(key, None)
            except VultrNotFoundError:
                self._world_refs.pop(key, None)
            except VultrControlError as exc:
                errors.append(f"destroy_world({world_ref}) failed: {exc}")

        self._destroying.discard(key)
        if errors:
            # Partial teardown failure: leave enough state that a
            # subsequent get_state/start_destroy retry can be attempted,
            # and surface the detail rather than silently reporting
            # DESTROYED for something that isn't.
            self._failed_detail[key] = "; ".join(errors)
        else:
            self._failed_detail.pop(key, None)
            self._destroyed.add(key)


__all__ = ["VultrAdaptedComputeProvider"]
