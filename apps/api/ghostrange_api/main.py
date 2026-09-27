from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import Settings
from .orphan_reaper import reap_orphans
from .event_gateway_factory import build_event_gateway
from .memory_events import MemoryEventGateway
from .health_routes import router as health_router
from .ops_routes import router as ops_router
from .ghostgate_bridge import prepare_promotion_after_golden
from .ghostgate_service import gate as ghostgate
from .golden_path import GoldenPathOrchestrator, GoldenScenarioId, assert_live_allowed
from .multiverse_fork import emit_fork_events, fork_remediation_worlds
from .orchestrator import M2OneWorldOrchestrator
from .scheduler_routes import router as scheduler_router
from .promotion_routes import router as promotion_router
from .ghostwatch_routes import router as ghostwatch_router
from .mesh_routes import router as mesh_router
from .causal_routes import router as causal_router
from .director_routes import router as director_router
from .production_routes import router as production_router
from .campaign_routes import router as campaign_router
from .artifact_registry import ArtifactRegistry
from .compute_provider import build_compute_provider
from .netbird_gate import build_netbird_client
from .worker_scheduler import WorkerScheduler
from .worker_store import WorkerStore
from .worker_routes import router as worker_router
from .worker_orchestrator import RealWorkerOrchestrator
from .inference_service import InferenceService
from .inference_router import build_inference_router
from .inference_worker_pool import InferenceWorkerPool
from .inference_worker_routes import router as inference_worker_router
from .investigation_routes import router as investigation_router
from .cost_routes import router as cost_router
from .cost_bridge import CostAccountingBridge
from .cost_persistence import CostLedgerPersistence
from .timing_store import OperationTimingStore
from .worlds_routes import router as worlds_router
from .timing_routes import router as timing_router
from ghostrange_cost.ledger import GhostCostLedger
from ghostrange_cost.money import usd_to_micros

logger = logging.getLogger("ghostrange.main")


async def _orphan_reaper_loop(app: FastAPI, settings: Settings) -> None:
    """Background safety-net sweep: periodically terminates any GhostRange-owned
    Vultr Compute VM that has outlived its ``ttl_seconds`` tag, regardless of
    which code path created it (see ``orphan_reaper.py``). This is the general
    fix for the class of incident where a worker VM is created but a crashed
    process / missed code path / manual test never tears it down again.

    Runs an immediate sweep at startup (catches anything already orphaned
    across a restart), then every ``settings.orphan_reaper_interval_s``.

    Resilient by construction at two layers: ``reap_orphans`` itself never
    raises for a single instance's termination failure (captured in its
    report's ``failed`` list instead), and this loop additionally wraps each
    *entire* sweep in a try/except so an unexpected error — e.g. the Vultr
    API being unreachable, or a bug in the reaper itself — is logged and the
    loop simply waits for the next interval, rather than dying silently and
    leaving GhostRange with no safety net until the next process restart.
    Blocking provider calls run in a worker thread via ``asyncio.to_thread``
    so a slow/real Vultr API call never stalls the event loop.
    """
    interval_s = max(30.0, settings.orphan_reaper_interval_s)
    logger.info("orphan-reaper: background sweep started (interval=%.0fs)", interval_s)
    while True:
        try:
            report = await asyncio.to_thread(reap_orphans, app.state.compute_provider, dry_run=False)
            if report["orphans_found"]:
                logger.info(
                    "orphan-reaper: sweep complete found=%d terminated=%d failed=%d still_present_after_reap=%d",
                    len(report["orphans_found"]),
                    len(report["terminated"]),
                    len(report["failed"]),
                    len(report["still_present_after_reap"]),
                )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - one bad sweep must never end the loop
            logger.exception("orphan-reaper: sweep raised an unexpected error, retrying next interval")
        try:
            await asyncio.sleep(interval_s)
        except asyncio.CancelledError:
            raise


def _build_inference_worker_pool(settings: Settings) -> InferenceWorkerPool:
    """Same GhostShield gateway construction as build_compute_provider — one mediated
    trusted-computing-base slice, shared mode, independent instance (separate action
    stream/permit set from the Compute worker gateway)."""
    from ghostrange_contracts.ghostshield_m17 import GhostShieldMode
    from ghostrange_ghostshield import GhostExecutionGateway

    try:
        mode = GhostShieldMode(settings.ghostshield_mode)
    except ValueError:
        mode = GhostShieldMode.SHADOW
    gateway = GhostExecutionGateway(mode=mode)
    inference = InferenceService(settings)
    return InferenceWorkerPool(settings, inference, gateway)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate_for_runtime()
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        gateway, _inner, pg_store = await build_event_gateway(
            settings.postgres_dsn,
            settings.redis_url,
            require_durable=settings.require_durable,
        )
        cost_ledger = GhostCostLedger()
        cost_ledger.configure_budget_cap_usd_micros(usd_to_micros(str(settings.max_campaign_cost_usd)))
        cost_persistence = None
        timing_store = None
        if pg_store is not None:
            cost_persistence = CostLedgerPersistence(pg_store._pool)  # noqa: SLF001
            await cost_persistence.ensure_schema()
            await cost_persistence.load_into(cost_ledger)
            timing_store = OperationTimingStore(pg_store._pool)
        cost_bridge = CostAccountingBridge(cost_ledger, persist=cost_persistence)
        orchestrator = M2OneWorldOrchestrator(
            gateway,
            range_dir=settings.range_dir,
            live_provider=settings.live_provider,
            settings=settings,
            cost_bridge=cost_bridge,
            timing_store=timing_store,
        )
        app.state.gateway = gateway
        app.state.orchestrator = orchestrator
        app.state.postgres_store = pg_store
        app.state.cost_ledger = cost_ledger
        app.state.cost_bridge = cost_bridge
        app.state.cost_persistence = cost_persistence
        app.state.timing_store = timing_store
        app.state.compute_provider = build_compute_provider(settings)
        app.state.orphan_reaper_task = None
        if settings.orphan_reaper_enabled:
            app.state.orphan_reaper_task = asyncio.create_task(
                _orphan_reaper_loop(app, settings), name="orphan-reaper-sweep"
            )
        # NetBird mesh client — None unless NETBIRD_ENABLED=true (current default: false,
        # fully inert). Not yet consumed by RealWorkerOrchestrator (see netbird_gate.py's
        # module docstring for the exact wiring still needed there); constructed here so
        # it's available as app.state.netbird_client for that follow-up without another
        # settings-parsing pass.
        app.state.netbird_client = build_netbird_client(settings)
        app.state.inference_worker_pool = _build_inference_worker_pool(settings)
        # Optional local Laya provider seam (INTELLIGENCE_PROVIDER=laya-local) — see
        # inference_router.py. Falls back to the pre-existing Vultr provider unchanged
        # when Laya isn't configured/active; never touches the inference worker pool above,
        # GhostExecutionGateway, or worker/cost accounting.
        app.state.inference_router = build_inference_router(settings)
        app.state.artifact_registry = None
        app.state.worker_store = None
        app.state.worker_orchestrator = None
        app.state.worker_scheduler = None
        if pg_store is not None:
            app.state.worker_store = WorkerStore(pg_store._pool)  # noqa: SLF001
            if settings.s3_configured:
                app.state.artifact_registry = ArtifactRegistry.from_settings(pg_store._pool, settings)  # noqa: SLF001
            app.state.worker_orchestrator = RealWorkerOrchestrator(
                settings,
                app.state.worker_store,
                app.state.compute_provider,
                app.state.artifact_registry,
                app.state.netbird_client,
            )
            app.state.worker_scheduler = WorkerScheduler(
                settings,
                pg_store._pool,
                app.state.compute_provider,
                app.state.artifact_registry,
                app.state.worker_orchestrator,
            )
        try:
            yield
        finally:
            reaper_task = app.state.orphan_reaper_task
            if reaper_task is not None:
                reaper_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await reaper_task
            if pg_store is not None:
                await pg_store.close()

    app = FastAPI(title="GhostRange API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    bootstrap_gateway = MemoryEventGateway()
    bootstrap_ledger = GhostCostLedger()
    bootstrap_ledger.configure_budget_cap_usd_micros(usd_to_micros(str(settings.max_campaign_cost_usd)))
    app.state.cost_ledger = bootstrap_ledger
    app.state.cost_bridge = CostAccountingBridge(bootstrap_ledger)
    app.state.gateway = bootstrap_gateway
    app.state.orchestrator = M2OneWorldOrchestrator(
        bootstrap_gateway,
        range_dir=settings.range_dir,
        live_provider=settings.live_provider,
        settings=settings,
        cost_bridge=app.state.cost_bridge,
    )
    app.state.postgres_store = None
    app.state.inference_worker_pool = _build_inference_worker_pool(settings)
    app.state.inference_router = build_inference_router(settings)

    app.include_router(health_router)
    app.include_router(ops_router)
    app.include_router(scheduler_router)
    app.include_router(worker_router)
    app.include_router(inference_worker_router)
    app.include_router(promotion_router)
    app.include_router(ghostwatch_router)
    app.include_router(mesh_router)
    app.include_router(causal_router)
    app.include_router(director_router)
    app.include_router(production_router)
    app.include_router(campaign_router)
    app.include_router(investigation_router)
    app.include_router(cost_router)
    app.include_router(worlds_router)
    app.include_router(timing_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {
            "ok": True,
            "live_provider": settings.live_provider,
            "live_enabled": settings.live_enabled,
            "golden_path": "ghostrange-tenant-escalation-v1",
        }

    @app.post("/v1/golden-path/runs")
    async def start_golden_path(
        request: Request,
        range_id: str | None = None,
        with_promotion: bool = False,
        scenario: GoldenScenarioId = "tenant_escalation",
    ):
        """M10 unified pipeline (mock by default). Optional M11 GhostGate promotion package."""
        if settings.live_enabled:
            try:
                assert_live_allowed()
            except RuntimeError as exc:
                raise HTTPException(403, str(exc)) from exc
        rid = uuid.UUID(range_id) if range_id else uuid.uuid4()
        gp = GoldenPathOrchestrator(
            repo_root=settings.repo_root,
            live=settings.live_enabled and settings.live_provider == "vultr",
            scenario=scenario,
        )
        gateway = request.app.state.gateway
        result = await gp.run_async(gateway, rid)
        promotion = None
        if with_promotion:
            promotion = await prepare_promotion_after_golden(gateway, result, ghostgate)
        return {
            "investigation_id": str(result.investigation_id),
            "campaign_id": str(result.campaign_id),
            "range_id": str(result.range_id),
            "scenario": result.scenario,
            "phases": result.phases,
            "benchmark": result.benchmark.to_json(),
            "bundle_digest": result.bundle_digest,
            "errors": result.errors,
            "promotion": promotion,
        }

    @app.post("/v1/ranges/{range_id}/runs/m2")
    async def start_m2_run(request: Request, range_id: str):
        try:
            rid = uuid.UUID(range_id)
        except ValueError as exc:
            raise HTTPException(400, "invalid range_id") from exc
        run = await request.app.state.orchestrator.start_run(rid)
        return {"range_id": str(run.range_id), "world_id": str(run.world_id), "status": run.status}

    @app.get("/v1/ranges/{range_id}/snapshot")
    async def snapshot(request: Request, range_id: str):
        try:
            rid = uuid.UUID(range_id)
        except ValueError as exc:
            raise HTTPException(400, "invalid range_id") from exc
        rows = await request.app.state.gateway.replay(rid, 0)
        return {
            "sequence": rows[-1].seq if rows else 0,
            "events": [r.to_client_event() for r in rows],
        }

    @app.get("/v1/ranges/{range_id}/stream")
    async def stream(range_id: str, request: Request, after: int = 0):
        try:
            rid = uuid.UUID(range_id)
        except ValueError as exc:
            raise HTTPException(400, "invalid range_id") from exc

        async def event_gen():
            async for row in request.app.state.gateway.stream(rid, after):
                if await request.is_disconnected():
                    break
                yield f"id: {row.seq}\ndata: {json.dumps(row.to_client_event())}\n\n"

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    @app.post("/v1/ranges/{range_id}/forks/multiverse")
    async def fork_multiverse(request: Request, range_id: str, branches: int = 3):
        try:
            rid = uuid.UUID(range_id)
        except ValueError as exc:
            raise HTTPException(400, "invalid range_id") from exc
        parent = uuid.uuid4()
        fork_result = fork_remediation_worlds(parent, count=branches)
        await emit_fork_events(request.app.state.gateway, rid, fork_result)
        return {
            "parent_world_id": str(fork_result.parent_world_id),
            "branches": [
                {"world_id": str(b.world_id), "label": b.branch_label} for b in fork_result.branches
            ],
        }

    @app.get("/v1/ranges/{range_id}/benchmark")
    async def benchmark(request: Request, range_id: str):
        try:
            rid = uuid.UUID(range_id)
        except ValueError as exc:
            raise HTTPException(400, "invalid range_id") from exc
        run = request.app.state.orchestrator._runs.get(rid)
        if not run:
            raise HTTPException(404, "no active run for range_id")
        return run.benchmark.to_json()

    return app


def cli() -> None:
    import uvicorn

    s = Settings.from_env()
    uvicorn.run(create_app(s), host=s.api_host, port=s.api_port, log_level="info")


if __name__ == "__main__":
    cli()
