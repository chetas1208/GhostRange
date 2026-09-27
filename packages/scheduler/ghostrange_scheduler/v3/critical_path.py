"""DAG critical-path analysis for scheduling priority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ghostrange_contracts.enums import TaskType
from ghostrange_contracts.scheduler_v3 import TaskLatencyModelV1


@dataclass(frozen=True)
class TaskTimingV1:
    task_id: str
    duration_seconds: float
    earliest_start: float
    latest_start: float
    slack_seconds: float
    on_critical_path: bool


def _build_adjacency(edges: Iterable[tuple[str, str]]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    successors: dict[str, list[str]] = {}
    predecessors: dict[str, list[str]] = {}
    for u, v in edges:
        successors.setdefault(u, []).append(v)
        predecessors.setdefault(v, []).append(u)
        successors.setdefault(v, successors.get(v, []))
        predecessors.setdefault(u, predecessors.get(u, []))
    return successors, predecessors


def analyze_critical_path(
    task_ids: list[str],
    edges: list[tuple[str, str]],
    latency_model: TaskLatencyModelV1,
    task_type_by_id: dict[str, str],
) -> dict[str, TaskTimingV1]:
    """Critical path method (CPM): ES/EF forward, LS/LF backward, slack = LS - ES."""
    if not task_ids:
        return {}

    succ, pred = _build_adjacency(edges)

    def _task_type(tid: str) -> TaskType:
        raw = task_type_by_id.get(tid, TaskType.VERIFY.value)
        try:
            return TaskType(raw)
        except ValueError:
            return TaskType.VERIFY

    duration = {tid: latency_model.estimate_seconds(_task_type(tid)) for tid in task_ids}

    indeg = {tid: len(pred.get(tid, [])) for tid in task_ids}
    queue = [tid for tid in task_ids if indeg[tid] == 0]
    order: list[str] = []
    while queue:
        queue.sort()
        u = queue.pop(0)
        order.append(u)
        for v in succ.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    if len(order) != len(task_ids):
        order = sorted(task_ids)

    es: dict[str, float] = {tid: 0.0 for tid in task_ids}
    ef: dict[str, float] = {tid: duration[tid] for tid in task_ids}
    for u in order:
        ef[u] = es[u] + duration[u]
        for v in succ.get(u, []):
            es[v] = max(es[v], ef[u])

    for u in order:
        ef[u] = es[u] + duration[u]
    project_finish = max(ef.values()) if task_ids else 0.0

    lf: dict[str, float] = {tid: project_finish for tid in task_ids}
    ls: dict[str, float] = {tid: project_finish - duration[tid] for tid in task_ids}
    for u in reversed(order):
        if succ.get(u):
            lf[u] = min(ls[v] for v in succ[u])
        else:
            lf[u] = project_finish
        ls[u] = lf[u] - duration[u]

    result: dict[str, TaskTimingV1] = {}
    for tid in task_ids:
        slack = ls[tid] - es[tid]
        result[tid] = TaskTimingV1(
            task_id=tid,
            duration_seconds=duration[tid],
            earliest_start=es[tid],
            latest_start=ls[tid],
            slack_seconds=slack,
            on_critical_path=slack <= 1e-6,
        )
    return result


__all__ = ["TaskTimingV1", "analyze_critical_path"]
