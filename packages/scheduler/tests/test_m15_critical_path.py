from uuid import uuid4

from ghostrange_contracts.enums import TaskType
from ghostrange_contracts.scheduler_m15 import ExecutionDAGNodeV2, ExecutionDAGV2, TaskResourceProfileV2
from ghostrange_scheduler.m15.critical_path import compute_critical_path_report


def _node(tid, deps, runtime):
    return ExecutionDAGNodeV2(
        task_id=tid,
        task_type=TaskType.REMEDIATE,
        dependency_ids=deps,
        resource_profile=TaskResourceProfileV2(
            task_id=tid,
            task_type=TaskType.REMEDIATE,
            cpu_min=1,
            cpu_preferred=1,
            ram_min_gb=1,
            ram_preferred_gb=1,
            expected_runtime_seconds=runtime,
        ),
    )


def test_critical_path_diamond():
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    dag = ExecutionDAGV2(
        range_id=uuid4(),
        nodes=[
            _node(a, [], 5),
            _node(b, [a], 10),
            _node(c, [a], 3),
            _node(d, [b, c], 2),
        ],
    )
    report = compute_critical_path_report(dag)
    assert report.estimated_makespan_seconds == 17  # 5+10+2
    assert report.critical_task_ids == [a, b, d]
