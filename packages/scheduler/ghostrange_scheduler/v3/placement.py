"""Heterogeneous placement: FIRST_FIT, BEST_FIT, COST_MIN helpers."""

from __future__ import annotations

from ghostrange_contracts.enums import ReasonCode, ResourceClass
from ghostrange_contracts.scheduler_v3 import (
    TaskResourceProfileV2,
    WorkerResourceProfileV2,
)


def worker_fits(profile: TaskResourceProfileV2, worker: WorkerResourceProfileV2) -> bool:
    if profile.gpu_required and worker.gpu_count < 1:
        return False
    if profile.gpu_memory_gb and worker.gpu_memory_gb and profile.gpu_memory_gb > worker.gpu_memory_gb:
        return False
    if profile.cpu_min > worker.cpu_cores:
        return False
    if profile.ram_min_gb > worker.ram_gb:
        return False
    region = profile.locality_constraints.get("region")
    if region and region != worker.region:
        return False
    return worker.state in ("READY", "BUSY")


def placement_score(profile: TaskResourceProfileV2, worker: WorkerResourceProfileV2) -> float:
    if not worker_fits(profile, worker):
        return -1.0
    cpu_slack = worker.cpu_cores - profile.cpu_preferred
    ram_slack = worker.ram_gb - profile.ram_preferred_gb
    load_penalty = worker.utilization
    cost_penalty = worker.estimated_hourly_cost_usd / 10.0
    return cpu_slack + ram_slack - load_penalty - cost_penalty


def select_worker_first_fit(
    profile: TaskResourceProfileV2,
    workers: list[WorkerResourceProfileV2],
) -> tuple[WorkerResourceProfileV2 | None, list[ReasonCode]]:
    for w in workers:
        if worker_fits(profile, w):
            return w, [ReasonCode.CPU_SUFFICIENT]
    return None, [ReasonCode.GPU_NOT_JUSTIFIED]


def select_worker_best_fit(
    profile: TaskResourceProfileV2,
    workers: list[WorkerResourceProfileV2],
) -> tuple[WorkerResourceProfileV2 | None, list[ReasonCode]]:
    best: WorkerResourceProfileV2 | None = None
    best_score = -1.0
    for w in workers:
        s = placement_score(profile, w)
        if s >= 0 and (best is None or s < best_score):
            best = w
            best_score = s
    if best:
        return best, [ReasonCode.CHEAP_INFORMATION_GAIN]
    return None, [ReasonCode.GPU_NOT_JUSTIFIED]


def choose_resource_class(profile: TaskResourceProfileV2) -> tuple[ResourceClass, list[ReasonCode]]:
    if profile.gpu_required:
        return ResourceClass.GPU_SMALL, [ReasonCode.GPU_ACCELERATION_EXPECTED]
    if profile.gpu_optional:
        return ResourceClass.CPU_MEDIUM, [ReasonCode.GPU_NOT_JUSTIFIED]
    return ResourceClass.CPU_SMALL, [ReasonCode.CPU_SUFFICIENT]


__all__ = [
    "worker_fits",
    "placement_score",
    "select_worker_first_fit",
    "select_worker_best_fit",
    "choose_resource_class",
]
