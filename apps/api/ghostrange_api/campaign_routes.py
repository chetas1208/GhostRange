"""M20 canonical campaign API."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Request

from .golden_path import assert_live_allowed
from .m20_campaign import M20CampaignOrchestrator, m20_response_payload

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
            try:
                bench = await request.app.state.worker_orchestrator.run_cpu_benchmark_test(
                    range_id=result.golden.range_id,
                    live=True,
                )
            except Exception as exc:
                result.errors.append(f"worker_benchmark:{exc.__class__.__name__}")
        result = orch.attach_live_worker_result(result, owned_workers=owned, worker_benchmark=bench)
        owned_after = provider.list_owned_workers(range_id=result.golden.range_id)
        result = orch.attach_live_worker_result(result, owned_workers=owned_after, worker_benchmark=bench)

    orchestrator = request.app.state.orchestrator
    asyncio.create_task(orchestrator.start_run(result.golden.range_id))

    return m20_response_payload(result)
