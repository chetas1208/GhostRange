"""Queue pressure metrics from scheduling context."""

from __future__ import annotations

from ghostrange_contracts.scheduler_v3 import QueueStateV1, SchedulingContextV3
from .critical_path import analyze_critical_path


def compute_queue_state(ctx: SchedulingContextV3) -> QueueStateV1:
    task_type_by_id = {str(t.id): t.task_type.value for t in ctx.tasks}
    edges = [(str(a), str(b)) for a, b in ctx.dependency_edges]
    all_ids = [str(t.id) for t in ctx.tasks]
    cp = analyze_critical_path(all_ids, edges, ctx.latency_model, task_type_by_id)
    critical_ready = sum(
        1 for tid in ctx.ready_task_ids if cp.get(str(tid)) and cp[str(tid)].on_critical_path
    )
    demand: dict[str, int] = {}
    for p in ctx.task_profiles:
        if p.gpu_required:
            demand["gpu"] = demand.get("gpu", 0) + 1
        else:
            demand["cpu"] = demand.get("cpu", 0) + 1
    return QueueStateV1(
        ready_count=len(ctx.ready_task_ids),
        blocked_count=max(0, len(ctx.tasks) - len(ctx.ready_task_ids) - len(ctx.running_task_ids)),
        running_count=len(ctx.running_task_ids),
        queue_wait_seconds_p95=ctx.queue_state.queue_wait_seconds_p95,
        oldest_wait_seconds=ctx.queue_state.oldest_wait_seconds,
        critical_ready_count=critical_ready,
        demand_by_resource_class=demand,
    )


__all__ = ["compute_queue_state"]
