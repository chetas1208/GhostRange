"""Provider-neutral ephemeral worker port (Vultr or mock)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from ghostrange_vultr_control import MockVultrProvider, RealVultrProvider
from ghostrange_vultr_control.models import CreateComputeRequest, CreateWorldRequest, GhostRangeTags

from .config import Settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class WorkerHandle:
    provider: str
    provider_compute_id: str
    world_ref: str
    region: str
    plan: str
    main_ip: str | None
    # Real creation timestamp and advisory TTL, carried through from the
    # underlying ComputeRecord/GhostRangeTags so a general-purpose orphan
    # reaper (see orphan_reaper.py) can compare age-vs-TTL without a second
    # round trip to the provider. created_at defaults to "now" only for
    # backward-compat construction sites (e.g. hand-rolled test doubles)
    # that predate this field and don't carry a real timestamp — every
    # production construction site below passes the real value explicitly.
    created_at: datetime = field(default_factory=_utc_now)
    ttl_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    score: float
    duration_ms: int
    notes: str


class ComputeProvider(Protocol):
    def create_worker(
        self,
        *,
        range_id: uuid.UUID,
        experiment_id: uuid.UUID | None,
        worker_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        user_data: str | None = None,
    ) -> WorkerHandle: ...
    def wait_ready(self, handle: WorkerHandle, *, timeout_s: float = 300.0) -> WorkerHandle: ...
    def run_benchmark(self, handle: WorkerHandle) -> BenchmarkResult: ...
    def terminate_worker(self, handle: WorkerHandle) -> None: ...
    def list_owned_workers(self, *, range_id: uuid.UUID | None = None) -> list[WorkerHandle]: ...


class MockComputeProvider:
    """Deterministic worker lifecycle without billable Vultr calls."""

    def __init__(self) -> None:
        self._vultr = MockVultrProvider()
        self._handles: dict[str, WorkerHandle] = {}

    def verify_api(self) -> None:
        self._vultr.list_computes()

    def list_all_ghostrange_workers(self) -> list[WorkerHandle]:
        return self.list_owned_workers(range_id=None)

    def create_worker(
        self,
        *,
        range_id: uuid.UUID,
        experiment_id: uuid.UUID | None,
        worker_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        user_data: str | None = None,
    ) -> WorkerHandle:
        tags = GhostRangeTags(
            range_id=str(range_id),
            world_id=str(worker_id or experiment_id) if (worker_id or experiment_id) else None,
            created_by="ghostscheduler",
            ttl_seconds=3600,
        )
        world = self._vultr.create_world(CreateWorldRequest(region="ewr", tags=tags, create_firewall_group=False))
        compute = self._vultr.create_compute(
            CreateComputeRequest(
                world_ref=world.provider_world_id,
                region="ewr",
                plan="vc2-1c-1gb",
                tags=tags,
                os_id=1743,
            )
        )
        handle = WorkerHandle(
            provider="mock",
            provider_compute_id=compute.provider_compute_id,
            world_ref=world.provider_world_id,
            region=compute.region,
            plan=compute.plan,
            main_ip=compute.main_ip,
            created_at=compute.created_at,
            ttl_seconds=tags.ttl_seconds,
        )
        self._handles[handle.provider_compute_id] = handle
        return handle

    def wait_ready(self, handle: WorkerHandle, *, timeout_s: float = 300.0) -> WorkerHandle:
        self._vultr.wait_until_ready(handle.provider_compute_id, timeout_s=timeout_s)
        return handle

    def run_benchmark(self, handle: WorkerHandle) -> BenchmarkResult:
        started = time.perf_counter()
        score = 42.0 + (hash(handle.provider_compute_id) % 100) / 10.0
        duration_ms = int((time.perf_counter() - started) * 1000) + 5
        return BenchmarkResult(score=score, duration_ms=duration_ms, notes="mock-cpu-benchmark")

    def terminate_worker(self, handle: WorkerHandle) -> None:
        self._vultr.destroy_compute(handle.provider_compute_id)
        self._handles.pop(handle.provider_compute_id, None)

    def list_owned_workers(self, *, range_id: uuid.UUID | None = None) -> list[WorkerHandle]:
        rid = str(range_id) if range_id else None
        out: list[WorkerHandle] = []
        for rec in self._vultr.list_computes(range_id=rid):
            out.append(
                WorkerHandle(
                    provider="mock",
                    provider_compute_id=rec.provider_compute_id,
                    world_ref=rec.world_ref or "",
                    region=rec.region,
                    plan=rec.plan,
                    main_ip=rec.main_ip,
                    created_at=rec.created_at,
                    ttl_seconds=rec.tags.ttl_seconds if rec.tags else None,
                )
            )
        return out


class VultrComputeProvider:
    """Live Vultr worker lifecycle — requires API key + worker VPC/plan env."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._vultr = RealVultrProvider(api_key=settings.vultr_api_key)

    def verify_api(self) -> None:
        """Read-only: raises if auth fails."""
        self._vultr.list_computes()

    def list_all_ghostrange_workers(self) -> list[WorkerHandle]:
        return self.list_owned_workers(range_id=None)

    def create_worker(
        self,
        *,
        range_id: uuid.UUID,
        experiment_id: uuid.UUID | None,
        worker_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        user_data: str | None = None,
    ) -> WorkerHandle:
        tags = GhostRangeTags(
            range_id=str(range_id),
            world_id=str(worker_id) if worker_id else (str(experiment_id) if experiment_id else None),
            created_by="ghostscheduler",
            ttl_seconds=self._settings.max_worker_lifetime_minutes * 60,
        )
        vpc_id = self._settings.vultr_worker_vpc_id
        if not vpc_id:
            raise RuntimeError("GHOSTRANGE_WORKER_VPC_ID required for live workers")
        suffix = str(worker_id or uuid.uuid4())[:8]
        compute = self._vultr.create_compute(
            CreateComputeRequest(
                world_ref=vpc_id,
                region=self._settings.vultr_worker_region,
                plan=self._settings.vultr_worker_plan,
                tags=tags,
                os_id=self._settings.vultr_worker_os_id,
                label=f"ghostrange-worker-{suffix}",
                hostname=f"gr-worker-{suffix}",
                user_data=user_data,
            )
        )
        return WorkerHandle(
            provider="vultr",
            provider_compute_id=compute.provider_compute_id,
            world_ref=vpc_id,
            region=compute.region,
            plan=compute.plan,
            main_ip=compute.main_ip,
            created_at=compute.created_at,
            ttl_seconds=tags.ttl_seconds,
        )

    def wait_ready(self, handle: WorkerHandle, *, timeout_s: float = 300.0) -> WorkerHandle:
        self._vultr.wait_until_ready(handle.provider_compute_id, timeout_s=timeout_s)
        refreshed = self._vultr.get_compute(handle.provider_compute_id)
        return WorkerHandle(
            provider=handle.provider,
            provider_compute_id=handle.provider_compute_id,
            world_ref=handle.world_ref,
            region=refreshed.region,
            plan=refreshed.plan,
            main_ip=refreshed.main_ip,
            created_at=refreshed.created_at,
            ttl_seconds=refreshed.tags.ttl_seconds if refreshed.tags else handle.ttl_seconds,
        )

    def run_benchmark(self, handle: WorkerHandle) -> BenchmarkResult:
        # Worker bootstrap not wired yet; score is deterministic placeholder until SSH/agent exists.
        started = time.perf_counter()
        duration_ms = int((time.perf_counter() - started) * 1000)
        return BenchmarkResult(
            score=1.0,
            duration_ms=duration_ms,
            notes="live worker ready; remote benchmark agent not deployed yet",
        )

    def terminate_worker(self, handle: WorkerHandle) -> None:
        self._vultr.destroy_compute(handle.provider_compute_id)

    def list_owned_workers(self, *, range_id: uuid.UUID | None = None) -> list[WorkerHandle]:
        rid = str(range_id) if range_id else None
        return [
            WorkerHandle(
                provider="vultr",
                provider_compute_id=rec.provider_compute_id,
                world_ref=rec.world_ref or "",
                region=rec.region,
                plan=rec.plan,
                main_ip=rec.main_ip,
                created_at=rec.created_at,
                ttl_seconds=rec.tags.ttl_seconds if rec.tags else None,
            )
            for rec in self._vultr.list_computes(range_id=rid)
        ]


def build_compute_provider(settings: Settings) -> ComputeProvider:
    from ghostrange_contracts.ghostshield_m17 import GhostShieldMode
    from ghostrange_ghostshield import GhostExecutionGateway

    from .shielded_compute import ShieldedComputeProvider

    if settings.live_only_runtime or settings.workers_live_only or (
        settings.scheduler_live and settings.vultr_api_key
    ):
        if not settings.vultr_worker_vpc_id:
            raise RuntimeError(
                "GHOSTRANGE_WORKER_VPC_ID required when GHOSTSCHEDULER_LIVE=true"
            )
        inner: ComputeProvider = VultrComputeProvider(settings)
    else:
        inner = MockComputeProvider()
    try:
        mode = GhostShieldMode(settings.ghostshield_mode)
    except ValueError:
        mode = GhostShieldMode.SHADOW
    if mode == GhostShieldMode.DISABLED:
        return inner
    gateway = GhostExecutionGateway(mode=mode)
    return ShieldedComputeProvider(inner, settings, gateway)
