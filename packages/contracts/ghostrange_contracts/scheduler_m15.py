"""M15 GhostScheduler adaptive compute contracts (additive to scheduler_v3).

Policy version target: ``ghostscheduler/m15``.
Live elastic fleet experiments require real-worker milestone GO + explicit flags.
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Literal, Optional

from pydantic import Field, model_validator

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import ReasonCode, ResourceClass, TaskType
from .scheduler_v3 import (
    CostEstimateKind,
    TaskResourceProfileV2,
    WorkerResourceProfileV2,
)


class ExecutionTaskState(str, Enum):
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    READY = "READY"
    QUEUED = "QUEUED"
    LEASED = "LEASED"
    RUNNING = "RUNNING"
    SPECULATIVE = "SPECULATIVE"
    CHECKPOINTING = "CHECKPOINTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class DependencyPolicy(str, Enum):
    ALL_REQUIRED = "ALL_REQUIRED"
    ANY_REQUIRED = "ANY_REQUIRED"
    QUORUM = "QUORUM"


class WorkerClassId(str, Enum):
    CPU_SMALL = "CPU_SMALL"
    CPU_MEDIUM = "CPU_MEDIUM"
    GPU_CLASS_X = "GPU_CLASS_X"  # profile/sim only unless ALLOW_LIVE_GPU_TEST


class WorkerClassV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    class_id: WorkerClassId
    vultr_plan_id: str = Field(..., description="From allowlisted config only")
    region: str
    resource_class: ResourceClass
    cpu_cores: float = Field(..., gt=0)
    ram_gb: float = Field(..., gt=0)
    gpu_count: int = Field(default=0, ge=0)
    estimated_hourly_cost_usd: float = Field(..., ge=0)
    measured_startup_p50_seconds: float = Field(default=0.0, ge=0)
    measured_startup_p95_seconds: float = Field(default=0.0, ge=0)
    live_provision_allowed: bool = Field(
        default=False,
        description="True only when class is on allowlist and env gates permit",
    )


class ExecutionDAGNodeV2(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "2"
    schema_version: Literal["2"] = "2"

    task_id: Id
    task_type: TaskType
    dependency_ids: list[Id] = Field(default_factory=list)
    dependency_policy: DependencyPolicy = DependencyPolicy.ALL_REQUIRED
    quorum_k: Optional[int] = Field(default=None, ge=1)
    resource_profile: TaskResourceProfileV2
    deadline_soft_at: Optional[AwareDatetime] = None
    deadline_hard_at: Optional[AwareDatetime] = None
    priority_hint: float = Field(default=0.0, ge=0, le=1, description="Director hint only")
    speculatable: bool = False
    cancellable: bool = True
    checkpointable: bool = True
    world_id: Optional[Id] = None
    experiment_id: Optional[Id] = None
    director_decision_id: Optional[Id] = None
    causal_intervention_id: Optional[Id] = None
    artifact_input_ids: list[Id] = Field(default_factory=list)
    artifact_output_ids: list[Id] = Field(default_factory=list)
    state: ExecutionTaskState = ExecutionTaskState.PENDING


class ExecutionDAGV2(VersionedModel):
    """Schedulable task DAG submitted to GhostScheduler (not Director epistemics)."""

    SCHEMA_VERSION: ClassVar[str] = "2"
    schema_version: Literal["2"] = "2"

    dag_id: Id = Field(default_factory=new_id)
    range_id: Id
    campaign_id: Optional[Id] = None
    revision: int = Field(default=1, ge=1)
    nodes: list[ExecutionDAGNodeV2] = Field(..., min_length=1)
    submitted_at: AwareDatetime = Field(default_factory=utc_now)
    simulation_only: bool = Field(
        default=False,
        description="When true, live Vultr provisioning must not occur",
    )

    @model_validator(mode="after")
    def _validate_dag(self) -> "ExecutionDAGV2":
        ids = {n.task_id for n in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("duplicate task_id in DAG")
        for n in self.nodes:
            for dep in n.dependency_ids:
                if dep not in ids:
                    raise ValueError(f"unknown dependency {dep} for task {n.task_id}")
            if n.dependency_policy == DependencyPolicy.QUORUM and not n.quorum_k:
                raise ValueError(f"quorum_k required for task {n.task_id}")
        # Cycle detection (DFS)
        graph = {n.task_id: n.dependency_ids for n in self.nodes}
        visiting: set[Id] = set()
        visited: set[Id] = set()

        def dfs(tid: Id) -> None:
            if tid in visiting:
                raise ValueError("DAG contains a cycle")
            if tid in visited:
                return
            visiting.add(tid)
            for d in graph[tid]:
                dfs(d)
            visiting.remove(tid)
            visited.add(tid)

        for tid in ids:
            dfs(tid)
        return self


class CriticalPathTaskV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    task_id: Id
    estimated_duration_seconds: float = Field(..., ge=0)
    slack_seconds: float = Field(..., ge=0)
    on_critical_path: bool = False


class CriticalPathReportV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    dag_id: Id
    dag_revision: int
    computed_at: AwareDatetime = Field(default_factory=utc_now)
    estimated_makespan_seconds: float = Field(..., ge=0)
    critical_task_ids: list[Id] = Field(default_factory=list)
    tasks: list[CriticalPathTaskV1] = Field(default_factory=list)
    model_version: str = "cpm_v1_estimated"


class TaskPriorityV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    task_id: Id
    score: float = Field(..., ge=0)
    critical_path_weight: float = Field(default=0.0, ge=0)
    downstream_block_count: int = Field(default=0, ge=0)
    deadline_slack_seconds: Optional[float] = None
    information_value: float = Field(
        default=0.0,
        ge=0,
        description="From GhostDirector; not LLM-invented priority",
    )
    reason_codes: list[ReasonCode] = Field(default_factory=list)


class ComputeCrossoverModelV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    task_id: Id
    cpu_class: WorkerClassId
    gpu_class: WorkerClassId
    cpu_completion_seconds: float = Field(..., ge=0)
    gpu_completion_seconds: float = Field(..., ge=0)
    gpu_startup_seconds: float = Field(..., ge=0)
    selected: Literal["cpu", "gpu"]
    margin_seconds: float = Field(..., description="positive => CPU wins by this margin")
    cost_kind: CostEstimateKind = CostEstimateKind.ESTIMATED


class PlacementDecisionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    task_id: Id
    selected_worker_id: Optional[Id] = None
    selected_worker_class: Optional[WorkerClassId] = None
    alternatives: list[str] = Field(default_factory=list)
    estimated_completion_seconds: float = Field(..., ge=0)
    incremental_cost_usd: float = Field(..., ge=0)
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    cost_kind: CostEstimateKind = CostEstimateKind.ESTIMATED


class SchedulerBudgetV2(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "2"
    schema_version: Literal["2"] = "2"

    campaign_budget_usd: float = Field(..., ge=0)
    experiment_budget_usd: float = Field(..., ge=0)
    max_active_workers: int = Field(default=1, ge=1)
    max_active_worlds: int = Field(default=1, ge=1)
    speculation_budget_usd: float = Field(default=0.0, ge=0)
    gpu_budget_usd: float = Field(default=0.0, ge=0)
    max_worker_lifetime_minutes: int = Field(default=15, ge=1)
    hard_cap_usd: float = Field(..., ge=0)


class SchedulerDecisionV2(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "2"
    schema_version: Literal["2"] = "2"

    decision_id: Id = Field(default_factory=new_id)
    decided_at: AwareDatetime = Field(default_factory=utc_now)
    dag_id: Id
    dag_revision: int
    fleet_revision: int = 0
    decision_type: str
    selected_action: str
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    estimated_cost_usd: float = Field(default=0.0, ge=0)
    estimated_latency_seconds: float = Field(default=0.0, ge=0)
    policy_version: str = "ghostscheduler/m15"
    model_advice: Optional[dict] = Field(
        default=None,
        description="Optional inference suggestion; never authoritative for provisioning",
    )
    cost_kind: CostEstimateKind = CostEstimateKind.ESTIMATED


# Re-export profile aliases for M15 docs (Wave 1 freeze names)
TaskResourceProfileV1 = TaskResourceProfileV2
WorkerResourceProfileV1 = WorkerResourceProfileV2

__all__ = [
    "ComputeCrossoverModelV1",
    "CriticalPathReportV1",
    "CriticalPathTaskV1",
    "DependencyPolicy",
    "ExecutionDAGNodeV2",
    "ExecutionDAGV2",
    "ExecutionTaskState",
    "PlacementDecisionV1",
    "SchedulerBudgetV2",
    "SchedulerDecisionV2",
    "TaskPriorityV1",
    "TaskResourceProfileV1",
    "WorkerClassId",
    "WorkerClassV1",
    "WorkerResourceProfileV1",
]
