"""GhostScheduler V3 contracts — multi-action plans, profiles, models, traces.

Additive to SchedulerDecisionV1/V2. Policy version: ``ghostscheduler/v3``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import ReasonCode, ResourceClass, TaskType
from .task import TaskV1


class SchedulerPolicyId(str, Enum):
    STATIC_SERIAL = "STATIC_SERIAL"
    STATIC_EQUAL_PARALLEL = "STATIC_EQUAL_PARALLEL"
    FIXED_POOL = "FIXED_POOL"
    FIRST_FIT = "FIRST_FIT"
    COST_MIN = "COST_MIN"
    GHOSTSCHEDULER_V3 = "GHOSTSCHEDULER_V3"
    FIXED_POOL_SAFE = "FIXED_POOL_SAFE"


class SchedulerActionKind(str, Enum):
    PLACE_TASK = "PLACE_TASK"
    CHANGE_PRIORITY = "CHANGE_PRIORITY"
    PROVISION_WORKER = "PROVISION_WORKER"
    DRAIN_WORKER = "DRAIN_WORKER"
    TERMINATE_WORKER = "TERMINATE_WORKER"
    SPECULATE_TASK = "SPECULATE_TASK"
    CANCEL_TASK = "CANCEL_TASK"
    CONTINUE_BRANCH = "CONTINUE_BRANCH"
    PRUNE_BRANCH = "PRUNE_BRANCH"
    STOP_EXPLORATION = "STOP_EXPLORATION"
    ROUTE_INFERENCE = "ROUTE_INFERENCE"
    DEFER_TASK = "DEFER_TASK"


class InferenceRoute(str, Enum):
    VULTR_SERVERLESS = "VULTR_SERVERLESS"
    LOCAL_CPU_MODEL = "LOCAL_CPU_MODEL"
    LOCAL_GPU_MODEL = "LOCAL_GPU_MODEL"
    DETERMINISTIC_NO_MODEL = "DETERMINISTIC_NO_MODEL"


class StragglerCause(str, Enum):
    WORKLOAD_SLOW = "WORKLOAD_SLOW"
    WORKER_SLOW = "WORKER_SLOW"
    NETWORK_SLOW = "NETWORK_SLOW"
    UNKNOWN = "UNKNOWN"


class CheckpointStrategy(str, Enum):
    NONE = "NONE"
    RESTARTABLE = "RESTARTABLE"
    STATEFUL = "STATEFUL"


class ReasoningBudgetLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CostEstimateKind(str, Enum):
    ESTIMATED = "ESTIMATED"
    MEASURED = "MEASURED"
    BILLED = "BILLED"


class TaskResourceProfileV2(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "2"
    schema_version: Literal["2"] = "2"

    task_id: Id
    task_type: TaskType
    cpu_min: float = Field(..., gt=0)
    cpu_preferred: float = Field(..., gt=0)
    ram_min_gb: float = Field(..., gt=0)
    ram_preferred_gb: float = Field(..., gt=0)
    gpu_required: bool = False
    gpu_optional: bool = False
    gpu_memory_gb: Optional[float] = Field(default=None, ge=0)
    network_intensity: float = Field(default=0.0, ge=0, le=1)
    disk_intensity: float = Field(default=0.0, ge=0, le=1)
    expected_runtime_seconds: float = Field(..., ge=0)
    parallelizable: bool = True
    preemptible: bool = False
    speculatable: bool = False
    cold_start_sensitive: bool = False
    model_inference: bool = False
    locality_constraints: dict[str, str] = Field(default_factory=dict)
    checkpoint_strategy: CheckpointStrategy = CheckpointStrategy.RESTARTABLE


class WorkerResourceProfileV2(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "2"
    schema_version: Literal["2"] = "2"

    worker_id: Id
    provider: str
    resource_class: ResourceClass
    cpu_cores: float = Field(..., gt=0)
    ram_gb: float = Field(..., gt=0)
    gpu_type: Optional[str] = None
    gpu_count: int = Field(default=0, ge=0)
    gpu_memory_gb: Optional[float] = Field(default=None, ge=0)
    network_class: str = "default"
    storage_class: str = "default"
    region: str = "default"
    state: str = Field(..., description="READY | BUSY | DRAINING | TERMINATING | TERMINATED")
    current_task_ids: list[Id] = Field(default_factory=list)
    utilization: float = Field(default=0.0, ge=0, le=1)
    estimated_hourly_cost_usd: float = Field(..., ge=0)
    startup_latency_seconds: float = Field(default=0.0, ge=0)
    remaining_min_lifetime_seconds: float = Field(default=0.0, ge=0)


class RuntimeDistributionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    task_type: TaskType
    count: int = Field(default=0, ge=0)
    mean_seconds: float = Field(default=0.0, ge=0)
    variance_seconds: float = Field(default=0.0, ge=0)
    p50_seconds: float = Field(default=0.0, ge=0)
    p75_seconds: float = Field(default=0.0, ge=0)
    p90_seconds: float = Field(default=0.0, ge=0)
    p95_seconds: float = Field(default=0.0, ge=0)
    p99_seconds: float = Field(default=0.0, ge=0)


class TaskLatencyModelV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    model_version: str = "task-latency/v1"
    distributions: list[RuntimeDistributionV1] = Field(default_factory=list)
    default_runtime_seconds: float = Field(default=60.0, gt=0)

    def estimate_seconds(self, task_type: TaskType) -> float:
        for d in self.distributions:
            if d.task_type == task_type and d.count > 0:
                return d.p50_seconds or d.mean_seconds
        return self.default_runtime_seconds


class ComputeCostModelV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    model_version: str = "compute-cost/v1"
    worker_usd_per_hour: dict[str, float] = Field(default_factory=dict)
    serverless_usd_per_1k_tokens: float = Field(default=0.002, ge=0)
    gpu_usd_per_hour: dict[str, float] = Field(default_factory=dict)

    def worker_hourly(self, resource_class: ResourceClass, fallback: float) -> float:
        key = resource_class.value
        return self.worker_usd_per_hour.get(key, fallback)


class ReasoningBudgetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    level: ReasoningBudgetLevel = ReasoningBudgetLevel.MEDIUM
    max_tokens: int = Field(default=2048, ge=0)
    num_samples: int = Field(default=1, ge=1)
    verification_calls: int = Field(default=0, ge=0)
    iterations: int = Field(default=1, ge=1)


class EvidenceValueModelV1(VersionedModel):
    """Optional exploration only — mandatory tests ignore this model."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    model_version: str = "evidence-value/v1"
    novelty_weight: float = 0.25
    coverage_weight: float = 0.25
    uncertainty_reduction_weight: float = 0.35
    verification_importance_weight: float = 0.15

    def expected_value(
        self,
        *,
        novelty: float,
        coverage: float,
        uncertainty_reduction: float,
        verification_importance: float,
        cost_usd: float,
        cost_floor: float = 0.01,
    ) -> float:
        num = (
            self.novelty_weight * novelty
            + self.coverage_weight * coverage
            + self.uncertainty_reduction_weight * uncertainty_reduction
            + self.verification_importance_weight * verification_importance
        )
        return num / max(cost_usd, cost_floor)


class QueueStateV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    ready_count: int = Field(default=0, ge=0)
    blocked_count: int = Field(default=0, ge=0)
    running_count: int = Field(default=0, ge=0)
    queue_wait_seconds_p95: float = Field(default=0.0, ge=0)
    oldest_wait_seconds: float = Field(default=0.0, ge=0)
    critical_ready_count: int = Field(default=0, ge=0)
    demand_by_resource_class: dict[str, int] = Field(default_factory=dict)


class FragmentationMetricsV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    cpu_fragmentation: float = Field(default=0.0, ge=0, le=1)
    ram_fragmentation: float = Field(default=0.0, ge=0, le=1)
    gpu_fragmentation: float = Field(default=0.0, ge=0, le=1)
    placement_failure_rate: float = Field(default=0.0, ge=0, le=1)


class SchedulingObjectiveWeightsV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    minimize_time_to_verified: float = 1.0
    minimize_compute_cost: float = 0.5
    minimize_idle_compute: float = 0.3
    minimize_wasted_speculation: float = 0.4
    maximize_verification_coverage: float = 1.0
    maximize_evidence_gain: float = 0.6
    maximize_utilization: float = 0.2


class PlanActionV1(VersionedModel):
    """One explainable scheduler action."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    decision_id: Id = Field(default_factory=new_id)
    action: SchedulerActionKind
    target_id: Id = Field(..., description="task, worker, world, or branch id")
    reason_codes: list[ReasonCode] = Field(..., min_length=1)
    input_features: dict[str, float] = Field(default_factory=dict)
    estimated_benefit: float = 0.0
    estimated_cost_usd: float = Field(default=0.0, ge=0)
    estimated_latency_seconds: float = Field(default=0.0, ge=0)
    confidence: float = Field(default=0.5, ge=0, le=1)
    constraints_considered: list[str] = Field(default_factory=list)
    policy_version: str = "ghostscheduler/v3"
    cost_kind: CostEstimateKind = CostEstimateKind.ESTIMATED
    inference_route: Optional[InferenceRoute] = None
    worker_id: Optional[Id] = None
    resource_class: Optional[ResourceClass] = None
    priority_delta: int = 0
    notes: Optional[str] = None
    timestamp: AwareDatetime = Field(default_factory=utc_now)


class SchedulingPlanV3(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "3"
    schema_version: Literal["3"] = "3"

    id: Id = Field(default_factory=new_id)
    range_id: Id
    policy_id: SchedulerPolicyId
    actions: list[PlanActionV1] = Field(default_factory=list)
    planning_duration_ms: float = Field(default=0.0, ge=0)
    created_at: AwareDatetime = Field(default_factory=utc_now)


class SchedulingContextV3(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "3"
    schema_version: Literal["3"] = "3"

    range_id: Id
    current_time: AwareDatetime = Field(default_factory=utc_now)
    policy_id: SchedulerPolicyId = SchedulerPolicyId.GHOSTSCHEDULER_V3
    tasks: list[TaskV1] = Field(default_factory=list)
    task_profiles: list[TaskResourceProfileV2] = Field(default_factory=list)
    workers: list[WorkerResourceProfileV2] = Field(default_factory=list)
    ready_task_ids: list[Id] = Field(default_factory=list)
    running_task_ids: list[Id] = Field(default_factory=list)
    dependency_edges: list[tuple[Id, Id]] = Field(
        default_factory=list, description="(from_task, to_task) must complete before to"
    )
    branch_world_ids: list[Id] = Field(default_factory=list)
    budget_remaining_usd: float = Field(..., ge=0)
    budget_hard_cap_usd: float = Field(..., gt=0)
    latency_model: TaskLatencyModelV1 = Field(default_factory=TaskLatencyModelV1)
    cost_model: ComputeCostModelV1 = Field(default_factory=ComputeCostModelV1)
    queue_state: QueueStateV1 = Field(default_factory=QueueStateV1)
    fragmentation: FragmentationMetricsV1 = Field(default_factory=FragmentationMetricsV1)
    objective_weights: SchedulingObjectiveWeightsV1 = Field(default_factory=SchedulingObjectiveWeightsV1)
    mandatory_task_ids: list[Id] = Field(
        default_factory=list, description="Must run — scheduler cannot STOP or skip"
    )
    provider_startup_seconds: dict[str, float] = Field(default_factory=dict)
    model_call_stats: dict[str, float] = Field(default_factory=dict)
    evidence_gain_per_branch: dict[str, float] = Field(default_factory=dict)


class SchedulerTraceEventV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    timestamp_ms: float
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SchedulerTraceV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    trace_id: Id = Field(default_factory=new_id)
    range_id: Id
    policy_id: SchedulerPolicyId
    seed: int = 0
    events: list[SchedulerTraceEventV1] = Field(default_factory=list)
    recorded_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = [
    "SchedulerPolicyId",
    "SchedulerActionKind",
    "InferenceRoute",
    "StragglerCause",
    "CheckpointStrategy",
    "ReasoningBudgetLevel",
    "CostEstimateKind",
    "TaskResourceProfileV2",
    "WorkerResourceProfileV2",
    "RuntimeDistributionV1",
    "TaskLatencyModelV1",
    "ComputeCostModelV1",
    "ReasoningBudgetV1",
    "EvidenceValueModelV1",
    "QueueStateV1",
    "FragmentationMetricsV1",
    "SchedulingObjectiveWeightsV1",
    "PlanActionV1",
    "SchedulingPlanV3",
    "SchedulingContextV3",
    "SchedulerTraceEventV1",
    "SchedulerTraceV1",
]
