"""Critical-path method on ExecutionDAGV2 (estimated durations)."""

from __future__ import annotations

from ghostrange_contracts.scheduler_m15 import (
    CriticalPathReportV1,
    CriticalPathTaskV1,
    ExecutionDAGV2,
)


def compute_critical_path_report(dag: ExecutionDAGV2) -> CriticalPathReportV1:
    """Longest path using node resource_profile.expected_runtime_seconds."""
    duration = {n.task_id: n.resource_profile.expected_runtime_seconds for n in dag.nodes}
    deps = {n.task_id: list(n.dependency_ids) for n in dag.nodes}
    memo: dict = {}

    def longest(tid):
        if tid in memo:
            return memo[tid]
        if not deps[tid]:
            memo[tid] = (duration[tid], [tid])
            return memo[tid]
        best_len, best_path = 0.0, []
        for d in deps[tid]:
            plen, ppath = longest(d)
            if plen > best_len:
                best_len, best_path = plen, ppath
        memo[tid] = (best_len + duration[tid], best_path + [tid])
        return memo[tid]

    makespan = 0.0
    critical_path: list = []
    for n in dag.nodes:
        ln, path = longest(n.task_id)
        if ln >= makespan:
            makespan = ln
            critical_path = path

    critical_set = set(critical_path)
    task_rows: list[CriticalPathTaskV1] = []
    finish = {tid: 0.0 for tid in duration}
    for n in dag.nodes:
        pred_finish = max((finish[d] for d in deps[n.task_id]), default=0.0)
        finish[n.task_id] = pred_finish + duration[n.task_id]
    for n in dag.nodes:
        slack = makespan - finish[n.task_id]
        task_rows.append(
            CriticalPathTaskV1(
                task_id=n.task_id,
                estimated_duration_seconds=duration[n.task_id],
                slack_seconds=max(0.0, slack),
                on_critical_path=n.task_id in critical_set,
            )
        )

    return CriticalPathReportV1(
        dag_id=dag.dag_id,
        dag_revision=dag.revision,
        estimated_makespan_seconds=makespan,
        critical_task_ids=critical_path,
        tasks=task_rows,
    )
