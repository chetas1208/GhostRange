"""M20 canonical campaign API."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Request

from .golden_path import GoldenScenarioId, assert_live_allowed
from .live_worker_fanout import compute_fan_out_count, run_worker_fan_out
from .m20_campaign import M20CampaignOrchestrator, m20_response_payload
from .worker_scheduler import BudgetExceededError

router = APIRouter(prefix="/v1/campaigns", tags=["campaigns"])


@router.post("/golden")
async def start_m20_golden_campaign(
    request: Request,
    range_id: str | None = None,
    scenario: GoldenScenarioId = "tenant_escalation",
):
    """One coordinated investigation: real golden-path components + M20 report/bundle + Arena."""
    settings = request.app.state.settings
    live = settings.live_enabled and settings.live_provider == "vultr"
    if live:
        try:
            assert_live_allowed()
        except RuntimeError as exc:
            raise HTTPException(403, str(exc)) from exc
        if not settings.workers_live_only:
            raise HTTPException(
                403,
                "Live M20 requires GHOSTSCHEDULER_LIVE, VULTR_API_KEY, GHOSTRANGE_WORKER_VPC_ID",
            )

    rid = uuid.UUID(range_id) if range_id else uuid.uuid4()
    compose = settings.golden_path_range_dir / "docker/vm-1/docker-compose.yml"
    if not compose.is_file():
        compose = settings.repo_root / "ranges/ghostrange-auth-lab-v1/docker/vm-1/docker-compose.yml"

    orch = M20CampaignOrchestrator(
        repo_root=settings.repo_root,
        compose_path=compose,
        live=live,
        deploy_sha=settings.deploy_sha,
        ghostshield_mode=settings.ghostshield_mode,
        inference_model=settings.inference_model,
        scenario=scenario,
    )
    gateway = request.app.state.gateway
    try:
        result = await orch.run_async(gateway, rid)
    except RuntimeError as exc:
        raise HTTPException(403, str(exc)) from exc

    if live and request.app.state.compute_provider is not None:
        provider = request.app.state.compute_provider
        owned = provider.list_owned_workers(range_id=result.golden.range_id)
        bench = None
        if request.app.state.worker_orchestrator is not None:
            # MAX_ACTIVE_COMPUTE_WORKERS must actually gate this call. Real
            # incident 2026-09-27: this call previously went straight to
            # run_cpu_benchmark_test() with no cap check at all (that check
            # lives in WorkerScheduler.run_benchmark_job(), which this path
            # never went through), and ShieldedComputeProvider's own
            # ownership-scoped check always saw 0 active workers because it
            # was scoped to this call's freshly-minted range_id. Both are
            # fixed now (see shielded_compute.py), but enforce the cap here
            # too, explicitly, as defense in depth on a public endpoint.
            if request.app.state.worker_scheduler is not None:
                try:
                    await request.app.state.worker_scheduler.assert_can_start_live_worker()
                except BudgetExceededError as exc:
                    raise HTTPException(429, str(exc)) from exc

            # Real parallel-worker fan-out. See live_worker_fanout.py for the
            # (directly unit-tested) reservation + isolation logic.
            cap = request.app.state.settings.compute_worker_concurrency_cap
            currently_owned = len(provider.list_all_ghostrange_workers())
            planned = result.golden.benchmark.worker_slots_planned or 1
            worker_fan_out = compute_fan_out_count(
                cap=cap, currently_owned=currently_owned, planned=planned
            )

            async def _one_worker() -> object:
                return await request.app.state.worker_orchestrator.run_cpu_benchmark_test(
                    range_id=result.golden.range_id,
                    live=True,
                )

            fan_out = await run_worker_fan_out(worker_fn=_one_worker, count=worker_fan_out)
            for exc in fan_out.failures:
                # A failed real-VM teardown must not be swallowed into a cosmetic
                # error string with no other signal - that's exactly how today's
                # 4 real orphaned VMs went unnoticed. Every failure is recorded,
                # not just the first.
                result.errors.append(f"worker_benchmark:{exc.__class__.__name__}: {exc}")
            if fan_out.successes:
                bench = fan_out.successes[0]  # legacy single-bench field, kept for compat
            result.worker_results = fan_out.to_summary()
            if fan_out.requested and not fan_out.successes and fan_out.failures:
                first = fan_out.failures[0]
                raise HTTPException(
                    500,
                    f"all {fan_out.failed} live worker attempt(s) failed - a real Vultr VM may "
                    "be left running; check /v1/scheduler/compute-dry-check. First error: "
                    f"{first.__class__.__name__}: {first}",
                ) from first
        result = orch.attach_live_worker_result(result, owned_workers=owned, worker_benchmark=bench)
        owned_after = provider.list_owned_workers(range_id=result.golden.range_id)
        result = orch.attach_live_worker_result(result, owned_workers=owned_after, worker_benchmark=bench)

    orchestrator = request.app.state.orchestrator
    asyncio.create_task(orchestrator.start_run(result.golden.range_id))

    return m20_response_payload(result)
