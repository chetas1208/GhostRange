import uuid

from ghostrange_contracts.cluster_state import ClusterStateV1
from ghostrange_contracts.enums import ReasonCode, ResourceClass
from ghostrange_contracts.task import ResourceProfileV1
from ghostrange_scheduler.resource_selection import select_resource_class


def _profile(**overrides) -> ResourceProfileV1:
    defaults = dict(cpu_cores=2.0, memory_gb=4.0)
    defaults.update(overrides)
    return ResourceProfileV1(**defaults)


def test_small_cpu_shape_selects_cpu_small():
    cls, reasons = select_resource_class(_profile(cpu_cores=1, memory_gb=2), None)
    assert cls == ResourceClass.CPU_SMALL
    assert reasons == []


def test_medium_cpu_shape_selects_cpu_medium():
    cls, reasons = select_resource_class(_profile(cpu_cores=6, memory_gb=16), None)
    assert cls == ResourceClass.CPU_MEDIUM


def test_large_cpu_shape_selects_cpu_large():
    cls, reasons = select_resource_class(_profile(cpu_cores=32, memory_gb=128), None)
    assert cls == ResourceClass.CPU_LARGE


def test_preferred_resource_class_is_honored():
    cls, _ = select_resource_class(_profile(preferred_resource_class=ResourceClass.CPU_LARGE), None)
    assert cls == ResourceClass.CPU_LARGE


def test_gpu_required_with_capacity_selects_gpu_and_flags_acceleration_expected():
    cluster = ClusterStateV1(
        range_id=uuid.uuid4(), capacity={ResourceClass.GPU_SMALL: 1}, in_use={}
    )
    cls, reasons = select_resource_class(_profile(gpu_required=True), cluster)
    assert cls in (ResourceClass.GPU_SMALL, ResourceClass.GPU_LARGE)
    assert ReasonCode.GPU_ACCELERATION_EXPECTED in reasons


def test_gpu_required_with_no_cluster_state_optimistically_assumes_capacity():
    cls, reasons = select_resource_class(_profile(gpu_required=True), None)
    assert cls in (ResourceClass.GPU_SMALL, ResourceClass.GPU_LARGE)
    assert ReasonCode.GPU_ACCELERATION_EXPECTED in reasons


def test_gpu_required_with_no_gpu_capacity_falls_back_to_cpu_and_flags_not_justified():
    cluster = ClusterStateV1(range_id=uuid.uuid4(), capacity={ResourceClass.CPU_SMALL: 4}, in_use={})
    cls, reasons = select_resource_class(_profile(gpu_required=True, cpu_cores=2, memory_gb=4), cluster)
    assert cls == ResourceClass.CPU_SMALL
    assert reasons == [ReasonCode.GPU_NOT_JUSTIFIED]


def test_gpu_capacity_fully_in_use_also_falls_back():
    cluster = ClusterStateV1(
        range_id=uuid.uuid4(),
        capacity={ResourceClass.GPU_SMALL: 1},
        in_use={ResourceClass.GPU_SMALL: 1},
    )
    cls, reasons = select_resource_class(_profile(gpu_required=True, cpu_cores=2, memory_gb=4), cluster)
    assert cls == ResourceClass.CPU_SMALL
    assert reasons == [ReasonCode.GPU_NOT_JUSTIFIED]


def test_selection_is_deterministic():
    profile = _profile(cpu_cores=4, memory_gb=8)
    a = select_resource_class(profile, None)
    b = select_resource_class(profile, None)
    assert a == b
