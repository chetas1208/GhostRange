import uuid

import pytest
from pydantic import ValidationError

from ghostrange_contracts.enums import WorldStatus
from ghostrange_contracts.world import WorldForkV1, WorldV1


def test_root_world_has_no_parent():
    world = WorldV1(range_id=uuid.uuid4(), label="root")
    assert world.parent_world_id is None
    assert world.status == WorldStatus.REQUESTED


def test_world_fork_carries_parent_and_child_ids():
    range_id = uuid.uuid4()
    parent = WorldV1(range_id=range_id, label="root")
    fork = WorldForkV1(
        range_id=range_id,
        parent_world_id=parent.id,
        child_world_id=uuid.uuid4(),
        fork_reason="branching to try remediation-a vs remediation-b",
        created_by="scheduler",
    )
    assert fork.parent_world_id == parent.id
    assert fork.fork_reason


def test_world_fork_requires_fork_reason():
    with pytest.raises(ValidationError):
        WorldForkV1(
            range_id=uuid.uuid4(),
            parent_world_id=uuid.uuid4(),
            child_world_id=uuid.uuid4(),
            created_by="scheduler",
        )
