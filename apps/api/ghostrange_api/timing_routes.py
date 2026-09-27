"""Operation timing: live run benchmark + historical percentiles."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["timing"])


@router.get("/v1/ranges/{range_id}/timing")
async def range_timing(request: Request, range_id: str, operation_type: str | None = None):
    try:
        rid = uuid.UUID(range_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid range_id") from exc
    orch = request.app.state.orchestrator
    run = orch._runs.get(rid)
    benchmark = run.benchmark.to_json() if run else {}
    rows = await request.app.state.gateway.replay(rid, 0)
    task_events = []
    for r in rows:
        ev = r.to_client_event()
        name = str(ev.get("event_name") or ev.get("type") or "")
        if name.startswith("task."):
            task_events.append({"type": name, "occurred_at": ev.get("occurred_at"), "task_id": ev.get("task_id")})

    settings = request.app.state.settings
    op_type = operation_type or "M2_RUN_TOTAL"
    historical = None
    estimate = {
        "elapsed_ms": benchmark.get("total_ms"),
        "estimated_total_ms": None,
        "estimated_remaining_ms": None,
        "estimate_basis": "INSUFFICIENT_DATA",
        "sample_count": 0,
    }
    store = getattr(request.app.state, "timing_store", None)
    if store is not None:
        summary = await store.summary(
            op_type,
            provider=settings.live_provider if settings.live_enabled else None,
            region=settings.vultr_worker_region if settings.live_enabled else None,
        )
        historical = summary.to_json()
        if run and benchmark.get("total_ms") is not None:
            estimate = store.estimate_remaining(summary, int(benchmark["total_ms"]))

    return {
        "range_id": range_id,
        "benchmark_decomposition": benchmark,
        "task_events": task_events,
        "operation_type": op_type,
        "historical": historical,
        "active_estimate": estimate,
        "estimate_source": estimate.get("estimate_basis", "INSUFFICIENT_DATA"),
    }
