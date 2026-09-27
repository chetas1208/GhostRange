"""Agent 25 — privacy-safe compute/workload priors (advisory only)."""

from __future__ import annotations

from dataclasses import dataclass

from ghostrange_contracts.ghostmesh_m13 import KnowledgeClass, MeshContributionV1


@dataclass
class SchedulerHintV1:
    resource_class: str
    expected_startup_sec: float
    provider_context: str
    advisory: bool = True


def hint_from_contribution(c: MeshContributionV1) -> SchedulerHintV1 | None:
    if c.knowledge_class != KnowledgeClass.SCHEDULER_PRIOR:
        return None
    ctx = c.applicability.runtime_class or "cpu_workload"
    return SchedulerHintV1(
        resource_class="CPU_MEDIUM" if "gpu" not in ctx.lower() else "GPU_SMALL",
        expected_startup_sec=45.0,
        provider_context=ctx,
    )
