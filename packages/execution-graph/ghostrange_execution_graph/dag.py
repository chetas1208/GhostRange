"""DAG utilities over contract types — no duplicate models."""

from __future__ import annotations

from ghostrange_contracts.execution_graph import DependencyEdgeV1, ExecutionGraphV1


class CycleError(ValueError):
    pass


def validate_acyclic(graph: ExecutionGraphV1) -> None:
    order = topological_order(graph)
    if len(order) != len(graph.task_ids):
        raise CycleError("cycle detected or disconnected tasks")


def topological_order(graph: ExecutionGraphV1) -> list:
    task_ids = list(graph.task_ids)
    incoming = {tid: 0 for tid in task_ids}
    adj: dict = {tid: [] for tid in task_ids}
    for edge in graph.edges:
        adj[edge.upstream_task_id].append(edge.downstream_task_id)
        incoming[edge.downstream_task_id] = incoming.get(edge.downstream_task_id, 0) + 1
    queue = [tid for tid in task_ids if incoming.get(tid, 0) == 0]
    order: list = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m in adj.get(n, []):
            incoming[m] -= 1
            if incoming[m] == 0:
                queue.append(m)
    return order


__all__ = ["topological_order", "validate_acyclic", "CycleError"]
