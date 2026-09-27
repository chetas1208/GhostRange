"""Replay SchedulerTraceV1 or synthetic workloads against baseline policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from ghostrange_contracts.enums import SecurityCriticality, TaskType
from ghostrange_contracts.scheduler_v3 import (
    SchedulerPolicyId,
    SchedulerTraceV1,
    SchedulingContextV3,
    SchedulingPlanV3,
)
from ghostrange_contracts.task import ResourceProfileV1, TaskV1

from ghostrange_scheduler.v3.plan import plan


@dataclass
class SimulationResult:
    policy_id: SchedulerPolicyId
    wall_time_ms: float = 0.0
    compute_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    idle_seconds: float = 0.0
    tasks_completed: int = 0
    tasks_cancelled: int = 0
    speculative_tasks: int = 0
    wasted_speculative_seconds: float = 0.0
    placement_failures: int = 0
    scheduler_overhead_ms: float = 0.0
    plans: list[SchedulingPlanV3] = field(default_factory=list)


class GhostSchedulerSimulator:
    def __init__(self, *, seed: int = 0) -> None:
        self.seed = seed

    def run_policy(
        self,
        ctx: SchedulingContextV3,
        *,
        ticks: int = 1,
    ) -> SimulationResult:
        result = SimulationResult(policy_id=ctx.policy_id)
        for _ in range(ticks):
            p = plan(ctx)
            result.plans.append(p)
            result.scheduler_overhead_ms += p.planning_duration_ms
            for a in p.actions:
                result.estimated_cost_usd += a.estimated_cost_usd
                result.compute_seconds += a.estimated_latency_seconds
                if a.action.value == "SPECULATE_TASK":
                    result.speculative_tasks += 1
        result.wall_time_ms = result.compute_seconds * 1000.0
        return result

    def from_trace(self, trace: SchedulerTraceV1, ctx: SchedulingContextV3) -> SimulationResult:
        ctx.policy_id = trace.policy_id
        return self.run_policy(ctx, ticks=max(1, len(trace.events) // 10))


def synthetic_mixed_branch_context(range_id=None) -> SchedulingContextV3:
    """Minimal 3-task DAG for simulator smoke tests."""
    from ghostrange_contracts.scheduler_v3 import TaskResourceProfileV2

    rid = range_id or uuid4()
    t1 = TaskV1(
        world_id=uuid4(),
        task_type=TaskType.REMEDIATE,
        resource_profile=ResourceProfileV1(cpu_cores=1, memory_gb=1),
        estimated_duration_seconds=30,
        estimated_cost_usd=0.01,
        expected_evidence_gain=0.5,
        uncertainty=0.4,
        security_criticality=SecurityCriticality.MEDIUM,
    )
    t2 = TaskV1(
        world_id=t1.world_id,
        task_type=TaskType.ATTACK,
        dependencies=[t1.id],
        resource_profile=ResourceProfileV1(cpu_cores=1, memory_gb=1),
        estimated_duration_seconds=20,
        estimated_cost_usd=0.01,
        expected_evidence_gain=0.8,
        uncertainty=0.2,
        security_criticality=SecurityCriticality.HIGH,
    )
    t3 = TaskV1(
        world_id=t1.world_id,
        task_type=TaskType.VERIFY,
        dependencies=[t1.id],
        resource_profile=ResourceProfileV1(cpu_cores=1, memory_gb=1),
        estimated_duration_seconds=15,
        estimated_cost_usd=0.01,
        expected_evidence_gain=0.6,
        uncertainty=0.1,
        security_criticality=SecurityCriticality.MEDIUM,
    )
    profiles = [
        TaskResourceProfileV2(
            task_id=t1.id,
            task_type=t1.task_type,
            cpu_min=1,
            cpu_preferred=1,
            ram_min_gb=1,
            ram_preferred_gb=1,
            expected_runtime_seconds=30,
        ),
        TaskResourceProfileV2(
            task_id=t2.id,
            task_type=t2.task_type,
            cpu_min=1,
            cpu_preferred=1,
            ram_min_gb=1,
            ram_preferred_gb=1,
            expected_runtime_seconds=20,
        ),
        TaskResourceProfileV2(
            task_id=t3.id,
            task_type=t3.task_type,
            cpu_min=1,
            cpu_preferred=1,
            ram_min_gb=1,
            ram_preferred_gb=1,
            expected_runtime_seconds=15,
        ),
    ]
    return SchedulingContextV3(
        range_id=rid,
        tasks=[t1, t2, t3],
        task_profiles=profiles,
        ready_task_ids=[t1.id],
        dependency_edges=[(t1.id, t2.id), (t1.id, t3.id)],
        budget_remaining_usd=10.0,
        budget_hard_cap_usd=10.0,
        mandatory_task_ids=[t1.id, t2.id, t3.id],
    )


__all__ = ["GhostSchedulerSimulator", "SimulationResult", "synthetic_mixed_branch_context"]
