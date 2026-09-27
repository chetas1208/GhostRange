"""Resource-class selection: map a TaskV1.resource_profile onto one of the
five ``ResourceClass`` values the contracts layer actually defines
(CPU_SMALL, CPU_MEDIUM, CPU_LARGE, GPU_SMALL, GPU_LARGE).

Deliberately NOT implementing a generic "SERVERLESS_INFERENCE" class: that
value does not exist in ``ghostrange_contracts.enums.ResourceClass`` today
(the M2 task brief explicitly says "only implement classes the current
architecture actually supports"). Vultr Serverless Inference is real
(docs/research/VULTR.md §3) and a reasonable future ResourceClass member
if/when an M2+ agent (11, per M2_COORDINATION.md wave 2, "Vultr Serverless
Inference planner") wires an inference-shaped task type through the
scheduler -- until then there is nothing in TaskV1/ResourceProfileV1 that
distinguishes "wants inference" from "wants a GPU box", so adding the enum
member now would be speculative, not additive-for-a-consumer.

Placement scoring (Tetris-style multi-resource alignment, per
SCHEDULING.md §2) is explicitly out of scope here: this module answers
"which class does this task's shape belong to", not "which specific node".
"""

from __future__ import annotations

from ghostrange_contracts.cluster_state import ClusterStateV1
from ghostrange_contracts.enums import ReasonCode, ResourceClass
from ghostrange_contracts.task import ResourceProfileV1

# CPU sizing thresholds. Deliberately simple, monotonic, and documented as
# tunable constants rather than implicit magic numbers -- v1 has no
# empirical workload data yet to fit these against (M2 has one range with
# modest services; see the task brief), so round numbers stand in until
# real utilization data justifies tuning them.
CPU_SMALL_MAX_CORES = 2.0
CPU_SMALL_MAX_MEMORY_GB = 4.0
CPU_MEDIUM_MAX_CORES = 8.0
CPU_MEDIUM_MAX_MEMORY_GB = 32.0
# Above CPU_MEDIUM thresholds -> CPU_LARGE.

GPU_SMALL_MAX_CORES = 8.0
GPU_SMALL_MAX_MEMORY_GB = 32.0
# Above GPU_SMALL thresholds (still GPU-required) -> GPU_LARGE.


def _cpu_class_for_shape(cpu_cores: float, memory_gb: float) -> ResourceClass:
    if cpu_cores <= CPU_SMALL_MAX_CORES and memory_gb <= CPU_SMALL_MAX_MEMORY_GB:
        return ResourceClass.CPU_SMALL
    if cpu_cores <= CPU_MEDIUM_MAX_CORES and memory_gb <= CPU_MEDIUM_MAX_MEMORY_GB:
        return ResourceClass.CPU_MEDIUM
    return ResourceClass.CPU_LARGE


def _gpu_class_for_shape(cpu_cores: float, memory_gb: float) -> ResourceClass:
    if cpu_cores <= GPU_SMALL_MAX_CORES and memory_gb <= GPU_SMALL_MAX_MEMORY_GB:
        return ResourceClass.GPU_SMALL
    return ResourceClass.GPU_LARGE


def select_resource_class(
    profile: ResourceProfileV1,
    cluster_state: ClusterStateV1 | None,
) -> tuple[ResourceClass, list[ReasonCode]]:
    """Deterministic, explainable resource-class selection.

    Returns ``(resource_class, reason_codes)``. ``reason_codes`` is empty
    for an ordinary CPU-only selection (selecting CPU_MEDIUM for a
    CPU_MEDIUM-shaped task needs no explanation beyond "that's its size");
    GPU involvement always produces exactly one of GPU_ACCELERATION_EXPECTED
    (GPU requested and available) or GPU_NOT_JUSTIFIED (GPU requested but
    the cluster currently has zero GPU capacity, so we fall back to the
    best CPU-only class for this task's shape rather than blocking it).

    Note on GPU_NOT_JUSTIFIED's name: SCHEDULING.md's Gandiva discussion
    (§3) frames this code around *runtime* GPU-utilization introspection
    (a running task using <15% of a GPU it was given). That live-utilization
    signal is explicitly out of M2 scope here (no runtime telemetry loop --
    see the README's "Out of scope" section). This module instead fires
    GPU_NOT_JUSTIFIED at *placement* time for the one case that IS in scope
    and uses the same code faithfully: the cluster cannot currently justify
    giving this task a GPU (none available), so it doesn't get one.
    """
    reasons: list[ReasonCode] = []

    if profile.preferred_resource_class is not None:
        chosen = profile.preferred_resource_class
    elif profile.gpu_required:
        chosen = _gpu_class_for_shape(profile.cpu_cores, profile.memory_gb)
    else:
        chosen = _cpu_class_for_shape(profile.cpu_cores, profile.memory_gb)

    is_gpu_class = chosen in (ResourceClass.GPU_SMALL, ResourceClass.GPU_LARGE)

    if profile.gpu_required or is_gpu_class:
        has_gpu_capacity = cluster_state is None or cluster_state.has_gpu_capacity()
        if not has_gpu_capacity:
            chosen = _cpu_class_for_shape(profile.cpu_cores, profile.memory_gb)
            reasons.append(ReasonCode.GPU_NOT_JUSTIFIED)
        else:
            reasons.append(ReasonCode.GPU_ACCELERATION_EXPECTED)

    return chosen, reasons


__all__ = [
    "CPU_SMALL_MAX_CORES",
    "CPU_SMALL_MAX_MEMORY_GB",
    "CPU_MEDIUM_MAX_CORES",
    "CPU_MEDIUM_MAX_MEMORY_GB",
    "GPU_SMALL_MAX_CORES",
    "GPU_SMALL_MAX_MEMORY_GB",
    "select_resource_class",
]
