"""M20 canonical campaign API."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Request

from .golden_path import assert_live_allowed
from .m20_campaign import M20CampaignOrchestrator, m20_response_payload
from .worker_scheduler import BudgetExceededError

router = APIRouter(prefix="/v1/campaigns", tags=["campaigns"])


@router.post("/golden")
async def start_m20_golden_campaign(request: Request, range_id: str | None = None):
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
            try:
                bench = await request.app.state.worker_orchestrator.run_cpu_benchmark_test(
                    range_id=result.golden.range_id,
                    live=True,
                )
            except Exception as exc:
                # A failed real-VM teardown must not be swallowed into a cosmetic
                # error string on an HTTP 200 - that's exactly how today's 4 real
                # orphaned VMs went unnoticed. Surface it loudly.
                result.errors.append(f"worker_benchmark:{exc.__class__.__name__}: {exc}")
                raise HTTPException(
                    500,
                    f"live worker step failed: {exc.__class__.__name__}: {exc} "
                    "- a real Vultr VM may be left running; check /v1/scheduler/compute-dry-check",
                ) from exc
        result = orch.attach_live_worker_result(result, owned_workers=owned, worker_benchmark=bench)
        owned_after = provider.list_owned_workers(range_id=result.golden.range_id)
        result = orch.attach_live_worker_result(result, owned_workers=owned_after, worker_benchmark=bench)

    orchestrator = request.app.state.orchestrator
    asyncio.create_task(orchestrator.start_run(result.golden.range_id))

    return m20_response_payload(result)
