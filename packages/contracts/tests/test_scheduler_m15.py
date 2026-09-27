import pytest
from uuid import uuid4

from ghostrange_contracts.enums import TaskType
from ghostrange_contracts.scheduler_m15 import (
    DependencyPolicy,
    ExecutionDAGNodeV2,
    ExecutionDAGV2,
    TaskResourceProfileV2,
)


def _profile(task_id):
    return TaskResourceProfileV2(
        task_id=task_id,
        task_type=TaskType.REMEDIATE,
        cpu_min=1,
        cpu_preferred=1,
        ram_min_gb=1,
        ram_preferred_gb=1,
        expected_runtime_seconds=10,
    )


def test_execution_dag_v2_diamond_valid():
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    rid = uuid4()
    dag = ExecutionDAGV2(
        range_id=rid,
        nodes=[
            ExecutionDAGNodeV2(task_id=a, task_type=TaskType.REMEDIATE, resource_profile=_profile(a)),
            ExecutionDAGNodeV2(
                task_id=b,
                task_type=TaskType.REMEDIATE,
                dependency_ids=[a],
                resource_profile=_profile(b),
            ),
            ExecutionDAGNodeV2(
                task_id=c,
                task_type=TaskType.REMEDIATE,
                dependency_ids=[a],
                resource_profile=_profile(c),
            ),
            ExecutionDAGNodeV2(
                task_id=d,
                task_type=TaskType.REMEDIATE,
                dependency_ids=[b, c],
                resource_profile=_profile(d),
            ),
        ],
    )
    assert dag.dag_id is not None


def test_execution_dag_v2_rejects_cycle():
    a, b = uuid4(), uuid4()
    with pytest.raises(ValueError, match="cycle"):
        ExecutionDAGV2(
            range_id=uuid4(),
            nodes=[
                ExecutionDAGNodeV2(
                    task_id=a,
                    task_type=TaskType.REMEDIATE,
                    dependency_ids=[b],
                    resource_profile=_profile(a),
                ),
                ExecutionDAGNodeV2(
                    task_id=b,
                    task_type=TaskType.REMEDIATE,
                    dependency_ids=[a],
                    resource_profile=_profile(b),
                ),
            ],
        )
