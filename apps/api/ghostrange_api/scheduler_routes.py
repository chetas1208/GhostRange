"""GhostScheduler V3 preview — no bypass of scheduler package."""

from __future__ import annotations

import uuid
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from ghostrange_contracts.scheduler_v3 import SchedulingContextV3
from ghostrange_scheduler.v3.plan import plan

from .orphan_reaper import reap_orphans
from .worker_scheduler import BudgetExceededError

router = APIRouter(prefix="/v1/scheduler", tags=["scheduler"])


def _owned_workers_safe(request: Request, *, live: bool) -> list:
    settings = request.app.state.settings
    provider = request.app.state.compute_provider
    if not live and not settings.workers_live_only:
        from .compute_provider import MockComputeProvider

        provider = MockComputeProvider()
    try:
        return provider.list_all_ghostrange_workers()
    except Exception:
        return []


@router.get("/guardrails")
async def scheduler_guardrails(request: Request):
    s = request.app.state.settings
    return {
        "scheduler_live": s.scheduler_live,
        "workers_live_only": s.workers_live_only,
        "live_provider": s.live_provider,
        "compute_configured": bool(s.vultr_api_key),
        "worker_vpc_configured": bool(s.vultr_worker_vpc_id),
        "max_active_workers": s.max_active_workers,
        "max_active_worlds": s.max_active_worlds,
        "max_experiment_cost_usd": s.max_experiment_cost_usd,
        "max_campaign_cost_usd": s.max_campaign_cost_usd,
        "max_worker_lifetime_minutes": s.max_worker_lifetime_minutes,
        "vultr_worker_region": s.vultr_worker_region,
        "vultr_worker_plan": s.vultr_worker_plan,
    }


@router.get("/compute-dry-check")
async def compute_dry_check(request: Request):
    """Authenticate to Vultr Compute API and list GhostRange-tagged instances (read-only)."""
    settings = request.app.state.settings
    if settings.vultr_api_key:
        from ghostrange_vultr_control import RealVultrProvider

        try:
            with RealVultrProvider(api_key=settings.vultr_api_key) as vultr:
                records = vultr.list_computes()
        except Exception as exc:
            return {
                "ok": False,
                "mode": "live_api",
                "scheduler_live": settings.scheduler_live,
                "worker_vpc_configured": bool(settings.vultr_worker_vpc_id),
                "error": type(exc).__name__,
                "error_detail": str(exc)[:200],
                "owned_worker_count": None,
                "owned_workers": [],
            }
        owned = [
            {
                "provider_compute_id": r.provider_compute_id,
                "region": r.region,
                "plan": r.plan,
                "main_ip": r.main_ip,
                "range_id": r.tags.range_id if r.tags else None,
            }
            for r in records
            if r.tags is not None
        ]
        mode = "live_api"
    else:
        if settings.scheduler_live:
            return {
                "ok": False,
                "mode": "live_api",
                "scheduler_live": settings.scheduler_live,
                "worker_vpc_configured": bool(settings.vultr_worker_vpc_id),
                "error": "MissingConfiguration",
                "error_detail": "VULTR_API_KEY required when GHOSTSCHEDULER_LIVE=true",
                "owned_worker_count": None,
                "owned_workers": [],
            }
        provider = request.app.state.compute_provider
        provider.verify_api()
        owned = [asdict(h) for h in provider.list_all_ghostrange_workers()]
        mode = "mock"
    return {
        "ok": True,
        "mode": mode,
        "scheduler_live": settings.scheduler_live,
        "worker_vpc_configured": bool(settings.vultr_worker_vpc_id),
        "owned_worker_count": len(owned),
        "owned_workers": owned,
    }


@router.post("/plan-preview")
async def plan_preview(range_id: str, budget_usd: float = 25.0):
    try:
        rid = uuid.UUID(range_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid range_id") from exc
    ctx = SchedulingContextV3(
        range_id=rid,
        budget_remaining_usd=budget_usd,
        budget_hard_cap_usd=max(budget_usd * 2, 50.0),
    )
    p = plan(ctx)
    return {
        "policy_id": p.policy_id.value if hasattr(p.policy_id, "value") else str(p.policy_id),
        "action_count": len(p.actions),
        "actions": [a.model_dump(mode="json") for a in p.actions[:20]],
        "trace_id": str(p.id) if hasattr(p, "id") else None,
    }


@router.post("/worker-benchmark")
async def worker_benchmark(request: Request, range_id: str, experiment_id: str | None = None):
    """Worker E2E — live Vultr when GHOSTSCHEDULER_LIVE is enabled (no mock fallback)."""
    settings = request.app.state.settings
    live = settings.workers_live_only
    if live:
        if not settings.vultr_worker_vpc_id:
            raise HTTPException(412, "GHOSTRANGE_WORKER_VPC_ID required")
    try:
        rid = uuid.UUID(range_id)
        eid = uuid.UUID(experiment_id) if experiment_id else None
    except ValueError as exc:
        raise HTTPException(400, "invalid uuid") from exc
    scheduler = getattr(request.app.state, "worker_scheduler", None)
    if scheduler is None:
        raise HTTPException(503, "worker scheduler not available (postgres required)")
    try:
        result = await scheduler.run_benchmark_job(range_id=rid, experiment_id=eid, live=live)
    except BudgetExceededError as exc:
        raise HTTPException(429, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    result["scheduler_mode"] = "live" if live else "mock"
    owned_after = _owned_workers_safe(request, live=live)
    result["owned_workers_after"] = len(owned_after)
    if live and owned_after:
        raise HTTPException(500, f"teardown failed: {len(owned_after)} owned workers remain")
    return result


@router.post("/live-worker-test")
async def live_worker_test(
    request: Request,
    range_id: str,
    live: bool = False,
    confirm: bool = False,
    experiment_id: str | None = None,
):
    """Billable Vultr worker proof — requires GHOSTSCHEDULER_LIVE and explicit live+confirm flags."""
    settings = request.app.state.settings
    if not live or not confirm:
        raise HTTPException(400, "set live=true and confirm=true to run billable worker test")
    if not settings.scheduler_live:
        raise HTTPException(403, "GHOSTSCHEDULER_LIVE is not enabled")
    if not settings.vultr_api_key:
        raise HTTPException(412, "VULTR_API_KEY required")
    if not settings.vultr_worker_vpc_id:
        raise HTTPException(412, "GHOSTRANGE_WORKER_VPC_ID required")
    try:
        rid = uuid.UUID(range_id)
        eid = uuid.UUID(experiment_id) if experiment_id else None
    except ValueError as exc:
        raise HTTPException(400, "invalid uuid") from exc
    scheduler = getattr(request.app.state, "worker_scheduler", None)
    if scheduler is None:
        raise HTTPException(503, "worker scheduler not available")
    try:
        result = await scheduler.run_benchmark_job(range_id=rid, experiment_id=eid, live=True)
    except BudgetExceededError as exc:
        raise HTTPException(429, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    result["scheduler_mode"] = "live"
    owned_after = _owned_workers_safe(request, live=True)
    result["owned_workers_after"] = len(owned_after)
    if owned_after:
        raise HTTPException(500, f"teardown failed: {len(owned_after)} owned workers remain")
    return result


@router.post("/reap-orphans")
async def reap_orphans_now(request: Request, dry_run: bool = True):
    """Manual on-demand trigger for the same general-purpose TTL orphan-reaper
    sweep that also runs automatically in the background (see main.py's
    lifespan / orphan_reaper.py) — terminates any GhostRange-owned Vultr
    Compute VM whose ttl_seconds tag has elapsed, regardless of which code
    path created it.

    Gated the same way ``/compute-dry-check`` and ``/live-worker-test`` are:
    no separate admin auth layer exists in this router (there is none to
    match — every sensitive action here is gated by an explicit request
    parameter plus Settings, not a bearer token), so the safety gate is
    ``dry_run`` itself: it defaults to ``true`` — a bare POST here never
    destroys anything — and the caller must explicitly pass
    ``dry_run=false`` to actually terminate found orphans. Always goes
    through ``request.app.state.compute_provider`` (the shielded provider
    built by ``build_compute_provider``), so GhostShield's ownership/policy
    checks gate every termination exactly as they do for every other
    teardown path in this API.
    """
    provider = request.app.state.compute_provider
    return reap_orphans(provider, dry_run=dry_run)


@router.get("/workers")
async def list_workers(request: Request, range_id: str | None = None):
    rid = None
    if range_id:
        try:
            rid = uuid.UUID(range_id)
        except ValueError as exc:
            raise HTTPException(400, "invalid range_id") from exc
    scheduler = getattr(request.app.state, "worker_scheduler", None)
    runs = []
    if scheduler is not None and rid is not None:
        runs = await scheduler.list_runs(rid)
    provider = request.app.state.compute_provider
    owned = provider.list_owned_workers(range_id=rid) if rid else provider.list_all_ghostrange_workers()
    return {"runs": runs, "owned_workers": [asdict(h) for h in owned]}


__all__ = ["router"]
