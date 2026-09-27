import uuid

from ghostrange_contracts.cluster_state import ClusterStateV1
from ghostrange_contracts.enums import ResourceClass, TaskType
from ghostrange_scheduler.parallelism import MAX_PARALLELISM_CAP, decide_parallelism


def test_provision_always_serializes_regardless_of_capacity():
    cluster = ClusterStateV1(range_id=uuid.uuid4(), capacity={ResourceClass.CPU_SMALL: 10}, in_use={})
    assert decide_parallelism(TaskType.PROVISION, ResourceClass.CPU_SMALL, cluster) == 1


def test_teardown_always_serializes():
    cluster = ClusterStateV1(range_id=uuid.uuid4(), capacity={ResourceClass.CPU_SMALL: 10}, in_use={})
    assert decide_parallelism(TaskType.TEARDOWN, ResourceClass.CPU_SMALL, cluster) == 1


def test_investigate_uses_available_capacity_up_to_cap():
    cluster = ClusterStateV1(range_id=uuid.uuid4(), capacity={ResourceClass.CPU_SMALL: 10}, in_use={})
    assert decide_parallelism(TaskType.INVESTIGATE, ResourceClass.CPU_SMALL, cluster) == MAX_PARALLELISM_CAP


def test_investigate_respects_low_available_capacity():
    cluster = ClusterStateV1(
        range_id=uuid.uuid4(), capacity={ResourceClass.CPU_SMALL: 3}, in_use={ResourceClass.CPU_SMALL: 1}
    )
    assert decide_parallelism(TaskType.INVESTIGATE, ResourceClass.CPU_SMALL, cluster) == 2


def test_no_cluster_state_defaults_to_one():
    assert decide_parallelism(TaskType.INVESTIGATE, ResourceClass.CPU_SMALL, None) == 1


def test_zero_available_capacity_floors_at_one():
    cluster = ClusterStateV1(
        range_id=uuid.uuid4(), capacity={ResourceClass.CPU_SMALL: 2}, in_use={ResourceClass.CPU_SMALL: 2}
    )
    assert decide_parallelism(TaskType.INVESTIGATE, ResourceClass.CPU_SMALL, cluster) == 1
