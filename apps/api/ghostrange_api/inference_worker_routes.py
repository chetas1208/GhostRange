"""HTTP surface for the real concurrent Vultr Serverless Inference worker pool."""

from __future__ import annotations

import uuid
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .inference_worker_pool import InferenceWorkerBudgetExceeded, InferenceWorkerTask

router = APIRouter(prefix="/v1/scheduler/inference-workers", tags=["inference-workers"])


class InferenceWorkerTaskIn(BaseModel):
    system: str = Field(default="You are a GhostRange investigation worker.")
    user: str = Field(..., min_length=1, max_length=4000)
    max_tokens: int = Field(default=256, ge=1, le=2000)
    label: str = ""


class DispatchBatchIn(BaseModel):
    tasks: list[InferenceWorkerTaskIn] = Field(..., min_length=1, max_length=50)
    campaign_id: str | None = None


@router.get("/guardrails")
async def inference_worker_guardrails(request: Request):
    settings = request.app.state.settings
    pool = getattr(request.app.state, "inference_worker_pool", None)
    return {
        "inference_configured": settings.inference_configured,
        "max_active_workers_configured": settings.max_active_workers,
        "concurrency_cap_effective": settings.inference_worker_concurrency_cap,
        "concurrency_hard_ceiling": settings.INFERENCE_WORKER_HARD_CEILING,
        "budget_cap_configured_usd": settings.inference_worker_max_usd,
        "budget_cap_effective_usd": settings.inference_worker_budget_cap_usd,
        "budget_hard_ceiling_usd": settings.INFERENCE_WORKER_BUDGET_HARD_CEILING_USD,
        "ghostshield_mode": settings.ghostshield_mode,
        "pool_ready": pool is not None,
    }


@router.post("/dispatch")
async def dispatch_inference_workers(request: Request, body: DispatchBatchIn):
    """Fan a batch of tasks out to up to MAX_ACTIVE_WORKERS concurrent real Vultr
    Serverless Inference calls, mediated by GhostExecutionGateway (P2 concurrency cap +
    budget hard cap enforced, not just logged)."""
    pool = getattr(request.app.state, "inference_worker_pool", None)
    if pool is None:
        raise HTTPException(503, "inference worker pool not available")
    if not pool.available:
        raise HTTPException(503, "inference not configured (VULTR_INFERENCE_API_KEY missing)")
    if body.campaign_id:
        try:
            pool._campaign_id = uuid.UUID(body.campaign_id)  # noqa: SLF001
        except ValueError as exc:
            raise HTTPException(400, "invalid campaign_id") from exc
    tasks = [
        InferenceWorkerTask(
            system=t.system, user=t.user, max_tokens=t.max_tokens, label=t.label or f"task-{i}"
        )
        for i, t in enumerate(body.tasks)
    ]
    try:
        result = await pool.dispatch_batch(tasks)
    except InferenceWorkerBudgetExceeded as exc:
        raise HTTPException(429, str(exc)) from exc
    return {
        "requested": result.requested,
        "dispatched": result.dispatched,
        "refused": result.refused,
        "max_observed_concurrency": result.max_observed_concurrency,
        "concurrency_cap": result.concurrency_cap,
        "spent_usd": result.spent_usd,
        "budget_cap_usd": result.budget_cap_usd,
        "ghostshield_mode": result.ghostshield_mode,
        "results": [asdict(r) for r in result.results],
    }


__all__ = ["router"]
