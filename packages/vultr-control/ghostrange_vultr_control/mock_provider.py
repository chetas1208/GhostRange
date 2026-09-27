"""MockVultrProvider: deterministic in-memory fake of the Vultr control
plane, implementing the exact same ``VultrControlProvider`` interface as
``RealVultrProvider``.

For unit tests, offline dev, and frontend/UI dev with no live Vultr
credentials. Every record it returns has ``provider=ProviderKind.MOCK`` —
this is stamped unconditionally by this class, never overridable by a
caller, so nothing downstream can construct a mock record that pretends to
be live infrastructure.

Determinism: ids are per-instance sequential counters (``mock-vpc-1``,
``mock-instance-1``, ...), not random/global, so two tests each constructing
their own ``MockVultrProvider()`` get the same, reproducible ids.

Timing model: by default (``instant=True``) every operation completes
immediately — good for fast unit tests. Passing ``instant=False`` with
``boot_delay_s`` / ``delete_delay_s`` simulates realistic provisioning/
teardown latency, so callers can test their own ``wait_until_ready`` /
``destroy_compute`` timeout-handling logic against something that actually
takes time, without needing live Vultr credentials or wall-clock minutes.
"""

from __future__ import annotations

import itertools
import threading
import time
from typing import Optional

from .errors import VultrNotFoundError, VultrTimeoutError, VultrValidationError
from .interface import VultrControlProvider
from .models import (
    ComputeRecord,
    CreateComputeRequest,
    CreateWorldRequest,
    ProviderKind,
    ResourceStatus,
    WorldRecord,
)


class MockVultrProvider(VultrControlProvider):
    def __init__(self, *, instant: bool = True, boot_delay_s: float = 0.0, delete_delay_s: float = 0.0) -> None:
        self._lock = threading.Lock()
        self._instant = instant
        self._boot_delay_s = boot_delay_s
        self._delete_delay_s = delete_delay_s

        self._world_seq = itertools.count(1)
        self._compute_seq = itertools.count(1)
        self._firewall_seq = itertools.count(1)

        self._worlds: dict[str, WorldRecord] = {}
        self._computes: dict[str, ComputeRecord] = {}
        self._compute_created_at: dict[str, float] = {}
        self._compute_delete_requested_at: dict[str, float] = {}

    # ---- world (VPC + firewall group) -----------------------------------

    def create_world(self, req: CreateWorldRequest) -> WorldRecord:
        vpc_id = f"mock-vpc-{next(self._world_seq)}"
        firewall_group_id: Optional[str] = None
        if req.create_firewall_group:
            firewall_group_id = f"mock-fwg-{next(self._firewall_seq)}"
        record = WorldRecord(
            provider=ProviderKind.MOCK,
            provider_world_id=vpc_id,
            firewall_group_id=firewall_group_id,
            region=req.region,
            v4_subnet=req.v4_subnet or "10.99.0.0",
            v4_subnet_mask=req.v4_subnet_mask if req.v4_subnet_mask is not None else 24,
            status=ResourceStatus.ACTIVE,
            tags=req.tags,
        )
        with self._lock:
            self._worlds[vpc_id] = record
        return record

    def get_world(self, provider_world_id: str) -> WorldRecord:
        with self._lock:
            record = self._worlds.get(provider_world_id)
        if record is None:
            raise VultrNotFoundError(f"mock vpc {provider_world_id} not found")
        return record

    def destroy_world(
        self,
        provider_world_id: str,
        *,
        firewall_group_id: Optional[str] = None,
        timeout_s: float = 120.0,
        poll_interval_s: float = 3.0,
    ) -> None:
        with self._lock:
            if provider_world_id not in self._worlds:
                raise VultrNotFoundError(f"mock vpc {provider_world_id} not found")
            del self._worlds[provider_world_id]
        # firewall_group_id has no independent record in this mock (it is
        # only ever tracked via WorldRecord.firewall_group_id) — deletion is
        # a no-op here, matching RealVultrProvider's best-effort cleanup
        # contract without needing a second in-memory table.

    def list_worlds(self, *, range_id: Optional[str] = None) -> list[WorldRecord]:
        with self._lock:
            records = list(self._worlds.values())
        owned = [r for r in records if r.tags is not None]
        if range_id is None:
            return owned
        return [r for r in owned if r.tags.range_id == range_id]

    # ---- compute (instances) ---------------------------------------------

    def create_compute(self, req: CreateComputeRequest) -> ComputeRecord:
        with self._lock:
            if req.world_ref not in self._worlds:
                raise VultrValidationError(
                    f"world {req.world_ref!r} does not exist in this MockVultrProvider "
                    "(create_world() must be called first, and world_ref must be that "
                    "call's provider_world_id)"
                )
            instance_id = f"mock-instance-{next(self._compute_seq)}"
            idx = int(instance_id.rsplit("-", 1)[-1])
            status = ResourceStatus.ACTIVE if self._instant else ResourceStatus.PENDING
            record = ComputeRecord(
                provider=ProviderKind.MOCK,
                provider_compute_id=instance_id,
                world_ref=req.world_ref,
                region=req.region,
                plan=req.plan,
                label=req.label,
                hostname=req.hostname or f"ghostrange-{instance_id}",
                main_ip=f"203.0.113.{idx % 256}",
                status=status,
                vultr_power_status="running" if status == ResourceStatus.ACTIVE else "stopped",
                vultr_server_status="ok" if status == ResourceStatus.ACTIVE else "none",
                tags=req.tags,
            )
            self._computes[instance_id] = record
            self._compute_created_at[instance_id] = time.monotonic()
        return record

    def get_compute(self, provider_compute_id: str) -> ComputeRecord:
        with self._lock:
            record = self._computes.get(provider_compute_id)
            if record is None:
                raise VultrNotFoundError(f"mock instance {provider_compute_id} not found")
            if record.status == ResourceStatus.PENDING and not self._instant:
                created_at = self._compute_created_at[provider_compute_id]
                if time.monotonic() - created_at >= self._boot_delay_s:
                    record = record.model_copy(
                        update={
                            "status": ResourceStatus.ACTIVE,
                            "vultr_power_status": "running",
                            "vultr_server_status": "ok",
                        }
                    )
                    self._computes[provider_compute_id] = record
            return record

    def wait_until_ready(
        self,
        provider_compute_id: str,
        *,
        timeout_s: float = 300.0,
        poll_interval_s: float = 5.0,
    ) -> ComputeRecord:
        deadline = time.monotonic() + timeout_s
        while True:
            record = self.get_compute(provider_compute_id)
            if record.status == ResourceStatus.ACTIVE:
                return record
            if time.monotonic() >= deadline:
                raise VultrTimeoutError(
                    f"mock instance {provider_compute_id} not active after {timeout_s}s "
                    f"(status={record.status.value})"
                )
            time.sleep(min(poll_interval_s, max(self._boot_delay_s, 0.01)))

    def destroy_compute(
        self,
        provider_compute_id: str,
        *,
        timeout_s: float = 120.0,
        poll_interval_s: float = 3.0,
    ) -> None:
        with self._lock:
            record = self._computes.get(provider_compute_id)
            if record is None:
                raise VultrNotFoundError(f"mock instance {provider_compute_id} not found")
            if self._instant:
                del self._computes[provider_compute_id]
                self._compute_created_at.pop(provider_compute_id, None)
                return
            self._computes[provider_compute_id] = record.model_copy(update={"status": ResourceStatus.DELETING})
            self._compute_delete_requested_at[provider_compute_id] = time.monotonic()

        deadline = time.monotonic() + timeout_s
        while True:
            with self._lock:
                requested_at = self._compute_delete_requested_at.get(provider_compute_id)
                if requested_at is None:
                    return  # already reaped by a concurrent caller
                if time.monotonic() - requested_at >= self._delete_delay_s:
                    self._computes.pop(provider_compute_id, None)
                    self._compute_created_at.pop(provider_compute_id, None)
                    self._compute_delete_requested_at.pop(provider_compute_id, None)
                    return
            if time.monotonic() >= deadline:
                raise VultrTimeoutError(f"mock instance {provider_compute_id} still present after {timeout_s}s; deletion not confirmed")
            time.sleep(min(poll_interval_s, max(self._delete_delay_s, 0.01)))

    def list_computes(self, *, range_id: Optional[str] = None) -> list[ComputeRecord]:
        """List GhostRange-owned instances only — mirrors
        ``RealVultrProvider.list_computes``'s ownership invariant: an
        untagged instance is never returned, even with ``range_id=None``.
        """
        with self._lock:
            records = list(self._computes.values())
        owned = [r for r in records if r.tags is not None]
        if range_id is None:
            return owned
        return [r for r in owned if r.tags.range_id == range_id]


__all__ = ["MockVultrProvider"]
