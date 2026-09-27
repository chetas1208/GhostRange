from uuid import uuid4

import pytest

from ghostrange_contracts.execution_graph import DependencyEdgeV1, ExecutionGraphV1
from ghostrange_execution_graph.dag import CycleError, topological_order, validate_acyclic


def test_topological_order():
    a, b, c = uuid4(), uuid4(), uuid4()
    g = ExecutionGraphV1(
        world_id=uuid4(),
        task_ids=[a, b, c],
        edges=[
            DependencyEdgeV1(upstream_task_id=a, downstream_task_id=b),
            DependencyEdgeV1(upstream_task_id=b, downstream_task_id=c),
        ],
    )
    order = topological_order(g)
    assert order.index(a) < order.index(b) < order.index(c)


def test_cycle_raises():
    a, b = uuid4(), uuid4()
    g = ExecutionGraphV1(
        world_id=uuid4(),
        task_ids=[a, b],
        edges=[
            DependencyEdgeV1(upstream_task_id=a, downstream_task_id=b),
            DependencyEdgeV1(upstream_task_id=b, downstream_task_id=a),
        ],
    )
    with pytest.raises(CycleError):
        validate_acyclic(g)
