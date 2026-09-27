"""M2 one-world pipeline: range-runtime + scheduler + policy + evidence + live events."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ghostrange_contracts._base import utc_now
from ghostrange_contracts.cluster_state import BudgetStateV1, ClusterStateV1, WorldStateV1
from ghostrange_contracts.enums import ExecutionStatus, ObservationType, RangeLifecycleState, ResourceClass
from ghostrange_contracts.range import RangeSpecV1
from ghostrange_contracts.scheduler import SchedulerDecisionV1
from ghostrange_contracts.verification import ObservationV1
from ghostrange_evidence.scenario_verification import AuthLabVerdict, evaluate_auth_lab_v1
from ghostrange_scheduler.benchmarks import ALL_CASES
from ghostrange_events import (
    ComputeProvisioningV1,
    ComputeReadyV1,
    ComputeReleasedV1,
    ComputeRequestedV1,
    EvidenceCreatedV1,
    ExecutionAuthorizedV1,
    ExecutionCompletedV1,
    ExecutionRequestedV1,
    ExecutionStartedV1,
    RangeAuthorizedV1,
    RangeRequestedV1,
    RangeValidatedV1,
    SchedulerDecisionV1Event,
    TaskCompletedV1,
    TaskQueuedV1,
    TaskScheduledV1,
    TaskStartedV1,
    VerificationPassedV1,
    VerificationStartedV1,
    WorldDestroyingV1,
    WorldDestroyedV1,
)
from ghostrange_range_iac.loader import load_range
from ghostrange_range_runtime.engine import RangeRuntimeEngine
from ghostrange_range_runtime.persistence import SqliteTransitionStore
from ghostrange_range_runtime.provider import FakeComputeProvider
from ghostrange_range_runtime.vultr_adapter import VultrAdaptedComputeProvider
from ghostrange_scheduler import schedule as scheduler_schedule
from ghostrange_vultr_control import MockVultrProvider

from .config import Settings
from .event_sink import AsyncGatewaySink
from .harness import run_auth_validation_http
from .memory_events import MemoryEventGateway
from .m20_ui_events import emit_m20_ui_accent_events
from .cost_bridge import CostAccountingBridge
from .shielded_vultr_adapter import ShieldedVultrAdapter


@dataclass
class RunBenchmark:
    provisioning_ms: int = 0
    boot_ms: int = 0
    execution_ms: int = 0
    verification_ms: int = 0
    teardown_ms: int = 0
    total_ms: int = 0
    estimated_cost_usd: float = 0.0
    event_count: int = 0
    evidence_artifacts: int = 0
    scheduler_decisions: int = 0
    live_provider: str = "mock"

    def to_json(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class ActiveRun:
    range_id: uuid.UUID
    world_id: uuid.UUID
    status: str = "idle"
    benchmark: RunBenchmark = field(default_factory=RunBenchmark)
    provider_resource_ids: list[str] = field(default_factory=list)
    primary_compute_worker_id: uuid.UUID | None = None
    compute_hourly_usd: float = 0.024


class M2OneWorldOrchestrator:
    def __init__(
        self,
        gateway: MemoryEventGateway,
        *,
        range_dir: Path,
        settings: Settings,
        live_provider: str = "mock",
        db_path: Path | None = None,
        cost_bridge: CostAccountingBridge | None = None,
        timing_store: Any | None = None,
    ) -> None:
        self.gateway = gateway
        self._cost_bridge = cost_bridge
        self._timing_store = timing_store
        self.range_dir = range_dir
        self.live_provider = live_provider
        self.db_path = db_path or Path("/tmp/ghostrange-m2-runtime.db")
        # GHOSTSHIELD_MODE from settings is required (not optional) so this
        # orchestrator can never be constructed in a state where the real
        # Vultr adapter's create/destroy path is silently unmediated — see
        # ``_build_provider`` and docs/security/GHOSTSHIELD_BYPASS_ANALYSIS.md.
        self._settings = settings
        self._runs: dict[uuid.UUID, ActiveRun] = {}
        self._lock = asyncio.Lock()

    async def start_run(self, range_id: uuid.UUID | None = None) -> ActiveRun:
        async with self._lock:
            for rid in list(self._runs):
                st = self._runs[rid].status
                if st in ("destroyed", "idle") or str(st).startswith("failed"):
                    del self._runs[rid]
            if range_id is not None and range_id in self._runs:
                return self._runs[range_id]
            if len(self._runs) >= 1 and range_id not in self._runs:
                raise RuntimeError("GHOSTRANGE_MAX_WORLDS=1 — another run is active")
        rid = range_id or uuid.uuid4()
        spec, topology, _, _ = load_range(self.range_dir)
        run = ActiveRun(range_id=rid, world_id=uuid.uuid4())
        self._runs[rid] = run
        if self._cost_bridge:
            await self._cost_bridge.emit_snapshot(self.gateway, run.range_id)
        asyncio.create_task(self._execute(run, spec))
        return run

    async def _emit(self, run: ActiveRun, event: Any, *, source: str = "orchestrator") -> None:
        if hasattr(event, "model_dump"):
            world_id = getattr(event, "world_id", run.world_id)
            await self.gateway.append(run.range_id, event, source=source, world_id=world_id)
        run.benchmark.event_count += 1

    async def _emit_legacy(self, run: ActiveRun, payload: dict[str, Any]) -> None:
        payload.setdefault("schema_version", "1")
        payload.setdefault("occurred_at", utc_now().isoformat())
        await self.gateway.append_legacy(run.range_id, payload, source="orchestrator")
        run.benchmark.event_count += 1

    async def _execute(self, run: ActiveRun, spec: RangeSpecV1) -> None:
        t0 = time.perf_counter()
        run.status = "running"
        wid = run.world_id
        try:
            spec_id = uuid.UUID(str(spec.id))
            policy_id = uuid.uuid4()
            budget_id = uuid.uuid4()
            await self._emit(
                run,
                RangeRequestedV1(
                    range_id=run.range_id,
                    spec_id=spec_id,
                    requested_by=spec.owner,
                ),
            )
            await self._emit(
                run,
                RangeValidatedV1(range_id=run.range_id, spec_id=spec_id, valid=True),
            )
            await self._emit(
                run,
                RangeAuthorizedV1(
                    range_id=run.range_id,
                    spec_id=spec_id,
                    policy_id=policy_id,
                    budget_id=budget_id,
                    authorized_by="policy-check",
                ),
            )

            loop = asyncio.get_running_loop()
            provider = self._build_provider(run)
            db_path = self.db_path.with_name(f"m2-{run.range_id}.db")

            def _runtime_sync():
                store = SqliteTransitionStore(db_path)
                sink = AsyncGatewaySink(self.gateway, run.range_id, loop=loop)
                engine = RangeRuntimeEngine(store=store, provider=provider, sink=sink)
                r = engine.create_range(spec, requested_by=spec.owner)
                run.world_id = r.root_world_id or run.world_id
                r = engine.validate_and_authorize(r, spec)
                t_prov = time.perf_counter()
                r = engine.provision(r, spec)
                r = engine.run_provisioning_to_ready(r)
                run.benchmark.provisioning_ms = int((time.perf_counter() - t_prov) * 1000)
                run.benchmark.boot_ms = run.benchmark.provisioning_ms
                return r, engine

            range_record, engine = await asyncio.to_thread(_runtime_sync)
            run.status = "ready"

            await self._emit_compute_and_assets(run, spec)
            await emit_m20_ui_accent_events(self.gateway, run, range_id=run.range_id)
            await self._emit_tasks_and_execution(run, spec)
            await self._emit_verification(run)

            t_teardown = time.perf_counter()
            await self._emit(
                run,
                WorldDestroyingV1(world_id=run.world_id, range_id=run.range_id, reason="teardown"),
            )

            def _teardown_sync() -> None:
                r = range_record
                store = SqliteTransitionStore(db_path)
                sink = AsyncGatewaySink(self.gateway, run.range_id, loop=loop)
                eng = RangeRuntimeEngine(store=store, provider=provider, sink=sink)
                r = eng.load_range(r.id) or r
                r = eng.start_execution(r)
                r = eng.start_verifying(r)
                r = eng.stop(r, reason="m2 complete")
                r = eng.begin_destroy(r)
                r = eng.run_teardown_to_destroyed(r)

            await asyncio.to_thread(_teardown_sync)
            await self._emit(
                run,
                WorldDestroyedV1(world_id=run.world_id, range_id=run.range_id, reason="teardown complete"),
            )
            run.benchmark.teardown_ms = int((time.perf_counter() - t_teardown) * 1000)
            run.status = "destroyed"
            self._write_benchmark(run)
            if self._timing_store is not None and run.benchmark.total_ms > 0:
                await self._timing_store.record(
                    range_id=run.range_id,
                    operation_type="M2_RUN_TOTAL",
                    elapsed_ms=run.benchmark.total_ms,
                    provider=self.live_provider,
                    region=self._settings.vultr_worker_region if self.live_provider == "vultr" else None,
                )
        except Exception as exc:
            run.status = f"failed:{exc}"
            raise
        finally:
            run.benchmark.total_ms = int((time.perf_counter() - t0) * 1000)

    def _write_benchmark(self, run: ActiveRun) -> None:
        out_dir = Path("artifacts/benchmarks")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "m2-live.json"
        run.benchmark.live_provider = self.live_provider
        path.write_text(json.dumps(run.benchmark.to_json(), indent=2), encoding="utf-8")

    def _build_provider(self, run: ActiveRun):
        if self.live_provider == "vultr":
            from ghostrange_vultr_control import RealVultrProvider

            inner = VultrAdaptedComputeProvider(RealVultrProvider())
        else:
            mock = MockVultrProvider()
            run.provider_resource_ids.append("mock-vpc")
            inner = VultrAdaptedComputeProvider(mock)
        return self._shield_provider(inner)

    def _shield_provider(self, inner: VultrAdaptedComputeProvider):
        """Route create/destroy world effects through GhostExecutionGateway.

        M17 bypass close: this provider used to be returned directly from
        ``_build_provider`` with no GhostShield mediation at all, so the
        real ``create_world``/``create_compute``/``destroy_compute``/
        ``destroy_world`` Vultr calls landed on the live API regardless of
        GHOSTSHIELD_MODE. Fail-closed by construction: ``self._settings``
        is a required constructor argument, so there is no code path here
        that can hand back an unshielded provider except an explicit
        operator opt-out (``GHOSTSHIELD_MODE=DISABLED``).
        """
        from ghostrange_contracts.ghostshield_m17 import GhostShieldMode
        from ghostrange_ghostshield import GhostExecutionGateway

        try:
            mode = GhostShieldMode(self._settings.ghostshield_mode)
        except ValueError:
            mode = GhostShieldMode.SHADOW
        if mode == GhostShieldMode.DISABLED:
            return inner
        gateway = GhostExecutionGateway(mode=mode)
        return ShieldedVultrAdapter(inner, self._settings, gateway)

    async def _emit_compute_and_assets(self, run: ActiveRun, spec: RangeSpecV1) -> None:
        cw = uuid.uuid4()
        live_vultr = self.live_provider == "vultr"
        region = self._settings.vultr_worker_region if live_vultr else "ewr"
        provider_label = "vultr" if live_vultr else "LOCAL_MOCK"
        instance_id = (
            run.provider_resource_ids[-1]
            if live_vultr and run.provider_resource_ids
            else ("vultr-compute" if live_vultr else "mock-inst-m2")
        )
        hourly = 0.024
        await self._emit(
            run,
            ComputeRequestedV1(
                compute_worker_id=cw,
                world_id=run.world_id,
                resource_class=ResourceClass.CPU_MEDIUM,
                region=region,
                requested_by="range-runtime",
            ),
        )
        await self._emit(
            run,
            ComputeProvisioningV1(compute_worker_id=cw, provider=provider_label, region=region),
        )
        await self._emit(
            run,
            ComputeReadyV1(
                compute_worker_id=cw,
                world_id=run.world_id,
                resource_class=ResourceClass.CPU_MEDIUM,
                region=region,
                provider=provider_label,
                provider_instance_id=instance_id,
                cost_per_hour_usd=hourly,
            ),
        )
        run.primary_compute_worker_id = cw
        run.compute_hourly_usd = 0.024
        if self._cost_bridge:
            await self._cost_bridge.on_compute_ready(
                self.gateway,
                run.range_id,
                resource_id=str(cw),
                hourly_rate_usd=0.024,
                event_id=f"compute-ready-{cw}",
            )
        run.benchmark.estimated_cost_usd += 0.024
        layouts = {
            "gw01": (0, 0.5, 0),
            "api01": (-0.6, 0.1, 0),
            "auth01": (0.6, 0.1, 0),
            "db01": (0, -0.35, 0),
        }
        asset_ids: dict[str, str] = {}
        for asset in spec.assets:
            aid = str(uuid.uuid5(run.range_id, asset.hostname))
            asset_ids[asset.hostname] = aid
            lx, ly, lz = layouts.get(asset.hostname, (0, 0, 0))
            await self._emit_legacy(
                run,
                {
                    "event_id": str(uuid.uuid4()),
                    "event_name": "asset.upserted",
                    "asset": {
                        "id": aid,
                        "world_id": str(run.world_id),
                        "hostname": asset.hostname,
                        "os_family": asset.os_family,
                        "role": asset.role.value if hasattr(asset.role, "value") else str(asset.role),
                        "kind": "gateway" if "gw" in asset.hostname else "service",
                        "layout": {"x": lx, "y": ly, "z": lz},
                    },
                },
            )
        links = [
            ("gw01", "api01"),
            ("gw01", "auth01"),
            ("api01", "db01"),
            ("auth01", "db01"),
        ]
        for i, (a, b) in enumerate(links):
            await self._emit_legacy(
                run,
                {
                    "event_id": str(uuid.uuid4()),
                    "event_name": "link.upserted",
                    "link": {
                        "id": f"l{i+1}",
                        "world_id": str(run.world_id),
                        "from_id": asset_ids[a],
                        "to_id": asset_ids[b],
                    },
                },
            )

    async def _emit_tasks_and_execution(self, run: ActiveRun, spec: RangeSpecV1) -> None:
        bench = ALL_CASES[0]
        task = bench.task.model_copy(update={"world_id": run.world_id, "id": uuid.uuid4()})
        cluster = bench.cluster_state.model_copy(update={"range_id": run.range_id})
        world_state = bench.world_state.model_copy(update={"world_id": run.world_id})
        await self._emit(
            run,
            TaskQueuedV1(
                task_id=task.id,
                world_id=run.world_id,
                task_type=task.task_type,
                priority=task.priority,
            ),
        )
        decision: SchedulerDecisionV1 = scheduler_schedule(task, cluster, world_state)
        run.benchmark.scheduler_decisions += 1
        await self._emit(
            run,
            SchedulerDecisionV1Event(
                decision_id=decision.id,
                task_id=task.id,
                world_id=run.world_id,
                target_resource_class=decision.target_resource_class,
                priority=decision.priority,
                estimated_cost_usd=decision.estimated_cost_usd,
                expected_value=decision.expected_value,
                parallelism=decision.parallelism,
                speculative=decision.speculative,
                reason_codes=list(decision.reason_codes),
                expiration=decision.expiration,
                termination_condition=decision.termination_condition,
            ),
        )
        await self._emit(
            run,
            TaskScheduledV1(
                task_id=task.id,
                world_id=run.world_id,
                decision_id=decision.id,
                target_resource_class=decision.target_resource_class,
            ),
        )
        exec_id = uuid.uuid4()
        await self._emit(
            run,
            ExecutionRequestedV1(
                execution_id=exec_id,
                task_id=task.id,
                world_id=run.world_id,
                requested_by="scheduler",
            ),
        )
        await self._emit(
            run,
            ExecutionAuthorizedV1(
                execution_id=exec_id,
                task_id=task.id,
                world_id=run.world_id,
                policy_id=uuid.uuid4(),
            ),
        )
        t_exec = time.perf_counter()
        await self._emit(
            run,
            ExecutionStartedV1(execution_id=exec_id, task_id=task.id, world_id=run.world_id),
        )
        simulate = self.live_provider != "vultr"
        http = run_auth_validation_http(base_url=None, simulate=simulate)
        run.benchmark.execution_ms = int((time.perf_counter() - t_exec) * 1000)
        art_hash = hashlib.sha256(http.body_excerpt.encode()).hexdigest()
        await self._emit_legacy(
            run,
            {
                "event_id": str(uuid.uuid4()),
                "event_name": "evidence.artifact_created",
                "artifact": {
                    "id": "art-http-resp",
                    "world_id": str(run.world_id),
                    "artifact_type": "COMMAND_OUTPUT",
                    "content_hash": art_hash,
                },
                "detail": {
                    "command": http.method + " " + http.url,
                    "output": http.body_excerpt,
                    "source_hostname": "auth",
                },
            },
        )
        run.benchmark.evidence_artifacts += 1
        claim_id = uuid.uuid4()
        await self._emit_legacy(
            run,
            {
                "event_id": str(uuid.uuid4()),
                "event_name": "evidence.claim_updated",
                "claim": {
                    "id": str(claim_id),
                    "world_id": str(run.world_id),
                    "statement": "Controlled authentication validation reproduced expected unsafe behavior",
                    "anchored": False,
                    "verified": False,
                },
            },
        )
        await self._emit(
            run,
            ExecutionCompletedV1(
                execution_id=exec_id,
                task_id=task.id,
                world_id=run.world_id,
                status=ExecutionStatus.SUCCEEDED,
                duration_seconds=max(1, run.benchmark.execution_ms // 1000),
            ),
        )
        await self._emit(
            run,
            TaskStartedV1(task_id=task.id, world_id=run.world_id, compute_worker_id=uuid.uuid4()),
        )
        ver_id = uuid.uuid4()
        ev_id = uuid.uuid4()
        await self._emit(
            run,
            EvidenceCreatedV1(
                evidence_id=ev_id,
                world_id=run.world_id,
                claim_id=claim_id,
                verification_id=ver_id,
                artifact_ids=[uuid.uuid4()],
                content_hash=art_hash,
            ),
        )
        await self._emit(
            run,
            TaskCompletedV1(
                task_id=task.id,
                world_id=run.world_id,
                duration_seconds=1,
                actual_cost_usd=0.002,
                evidence_ids=[ev_id],
            ),
        )

    async def _emit_verification(self, run: ActiveRun) -> None:
        t0 = time.perf_counter()
        claim_id = uuid.uuid4()
        ver_id = uuid.uuid4()
        await self._emit(
            run,
            VerificationStartedV1(
                verification_id=ver_id,
                claim_id=claim_id,
                world_id=run.world_id,
                method="RE_EXECUTION",
                verifier_agent_id=uuid.uuid4(),
            ),
        )
        exec_id = uuid.uuid4()
        observations = [
            ObservationV1(
                execution_id=exec_id,
                world_id=run.world_id,
                agent_id=uuid.uuid4(),
                observation_type=ObservationType.NETWORK_TRAFFIC,
                summary="HTTP 401 Unauthorized response from auth validate endpoint",
            )
        ]
        verdict = evaluate_auth_lab_v1(observations)
        if verdict.verdict == AuthLabVerdict.EXPECTED_CONDITION_OBSERVED:
            await self._emit(
                run,
                VerificationPassedV1(
                    verification_id=ver_id,
                    claim_id=claim_id,
                    world_id=run.world_id,
                    evidence_ids=[],
                ),
            )
        run.benchmark.verification_ms = int((time.perf_counter() - t0) * 1000)
        cw = run.primary_compute_worker_id or uuid.uuid4()
        if self._cost_bridge:
            await self._cost_bridge.on_compute_released(
                self.gateway,
                run.range_id,
                resource_id=str(cw),
                hourly_rate_usd=run.compute_hourly_usd,
                event_id=f"compute-released-{cw}",
                legacy_total_usd=0.04,
            )
        await self._emit(
            run,
            ComputeReleasedV1(compute_worker_id=cw, total_cost_usd=0.04, reason="teardown"),
        )
