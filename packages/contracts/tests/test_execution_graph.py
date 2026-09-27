import uuid

import pytest
from pydantic import ValidationError

from ghostrange_contracts.execution_graph import DependencyEdgeV1, ExecutionGraphV1


def test_dependency_edge_rejects_self_loop():
    task_id = uuid.uuid4()
    with pytest.raises(ValidationError):
        DependencyEdgeV1(upstream_task_id=task_id, downstream_task_id=task_id)


def test_execution_graph_valid_edges():
    world_id = uuid.uuid4()
    t1, t2 = uuid.uuid4(), uuid.uuid4()
    graph = ExecutionGraphV1(
        world_id=world_id,
        task_ids=[t1, t2],
        edges=[DependencyEdgeV1(upstream_task_id=t1, downstream_task_id=t2)],
    )
    assert len(graph.edges) == 1


def test_execution_graph_rejects_edge_to_unknown_task():
    world_id = uuid.uuid4()
    t1, t2, unknown = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    with pytest.raises(ValidationError):
        ExecutionGraphV1(
            world_id=world_id,
            task_ids=[t1, t2],
            edges=[DependencyEdgeV1(upstream_task_id=t1, downstream_task_id=unknown)],
        )
