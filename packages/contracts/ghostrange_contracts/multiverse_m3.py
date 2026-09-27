"""M3 multiverse contracts (additive — does not replace M1/M2 V1 shapes).

RemediationPlanV1 is the structured planner output; RemediationV1 in
``hypothesis.py`` remains the record of an applied remediation in a world.
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import ReasonCode, ResourceClass, VerificationResult
from .scheduler import SchedulerDecisionV1


class ForkStrategy(str, Enum):
    TEMPLATE_REPLAY = "template_replay"
    SNAPSHOT_CLONE = "snapshot_clone"
    IMAGE_REPLAY = "image_replay"
    CONTAINER_SNAPSHOT = "container_snapshot"


class RemediationChangeType(str, Enum):
    CONFIG_PATCH = "config_patch"
    MIDDLEWARE_POLICY = "middleware_policy"
    SERVICE_AUTH_CONFIG = "service_auth_config"
    PACKAGE_UPDATE = "package_update"
    CONTAINER_IMAGE = "container_image"
    SERVICE_RESTART = "service_restart"


class RemediationActionKind(str, Enum):
    CONFIG_PATCH = "config_patch"
    SERVICE_RESTART = "service_restart"
    PACKAGE_UPDATE = "package_update"
    CONTAINER_IMAGE_CHANGE = "container_image_change"


class RemediationActionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    kind: RemediationActionKind
    target_asset_ids: list[Id] = Field(default_factory=list)
    parameters: dict[str, str] = Field(default_factory=dict)
    rollback_hint: Optional[str] = None


class RemediationPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    title: str
    description: str
    target_asset_ids: list[Id] = Field(default_factory=list)
    change_type: RemediationChangeType
    actions: list[RemediationActionV1] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    expected_effect: str
    potential_regressions: list[str] = Field(default_factory=list)
    risk_notes: Optional[str] = None
    estimated_runtime_seconds: float = Field(..., ge=0)
    estimated_cost_usd: float = Field(..., ge=0)
    rollback_strategy: Optional[str] = None
    source: str = Field(..., description="human | serverless_inference | fixture")
    test_only: bool = False


class WorldFingerprintV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    world_id: Id
    template_version: Optional[str] = None
    provider_image_id: Optional[str] = None
    application_artifact_hash: Optional[str] = None
    config_hash: Optional[str] = None
    scenario_version: str = "1"
    data_seed_hash: Optional[str] = None
    captured_at: AwareDatetime = Field(default_factory=utc_now)


class WorldForkV2(VersionedModel):
    """M3 fork record — superset of WorldForkV1 semantics for lineage + isolation."""

    SCHEMA_VERSION: ClassVar[str] = "2"
    schema_version: Literal["2"] = "2"

    id: Id = Field(default_factory=new_id)
    range_id: Id
    base_world_id: Id
    parent_world_id: Id
    child_world_id: Id
    remediation_id: Id
    fork_generation: int = Field(..., ge=0)
    fork_strategy: ForkStrategy
    creation_reason: str
    inherited_state_reference: str = Field(
        ..., description="Content-addressed or provider snapshot ref at fork point"
    )
    fork_point_fingerprint: WorldFingerprintV1
    requested_resource_profile: ResourceClass
    budget_slice_usd: Optional[float] = Field(default=None, ge=0)
    triggered_by_decision_id: Optional[Id] = None
    created_by: str
    created_at: AwareDatetime = Field(default_factory=utc_now)


class AttackReplayActionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    kind: str
    target_asset_id: Id
    parameters: dict[str, str] = Field(default_factory=dict)


class AttackReplayPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    scenario_id: str
    target_asset_ids: list[Id] = Field(default_factory=list)
    actions: list[AttackReplayActionV1] = Field(default_factory=list)
    expected_baseline_observation: str
    verification_condition: str
    timeout_seconds: float = Field(..., gt=0)
    safety_policy_id: Optional[Id] = None


class VerificationSuiteV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    reproduction_test_ids: list[str] = Field(default_factory=list)
    adversarial_replay_plan_id: Id
    regression_test_ids: list[str] = Field(default_factory=list)
    service_health_test_ids: list[str] = Field(default_factory=list)
    optional_path_test_ids: list[str] = Field(default_factory=list)
    version: str = "1"


class WorldEvaluationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    world_id: Id
    remediation_id: Id
    original_attack_blocked: bool
    regressions_passed: bool
    alternative_tests_passed: bool
    evidence_count: int = Field(..., ge=0)
    unresolved_findings: list[str] = Field(default_factory=list)
    runtime_seconds: float = Field(..., ge=0)
    compute_cost_usd: float = Field(..., ge=0)
    model_cost_usd: float = Field(default=0, ge=0)
    verification_status: VerificationResult
    confidence_explanation: str
    limitations: list[str] = Field(default_factory=list)


class BranchStateV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    world_id: Id
    remediation_id: Id
    security_criticality: float = Field(..., ge=0, le=1)
    remaining_uncertainty: float = Field(..., ge=0, le=1)
    verification_progress: float = Field(..., ge=0, le=1)
    expected_evidence_gain: float = Field(..., ge=0)
    estimated_remaining_cost_usd: float = Field(..., ge=0)
    estimated_remaining_runtime_seconds: float = Field(..., ge=0)
    failure_signals: list[str] = Field(default_factory=list)


class EvidenceStateV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    range_id: Id
    per_world_artifact_counts: dict[str, int] = Field(default_factory=dict)
    last_evidence_gain_at: Optional[AwareDatetime] = None


class SchedulingContextV2(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "2"
    schema_version: Literal["2"] = "2"

    range_id: Id
    cluster_state_ref: str = Field(..., description="Id or snapshot ref to ClusterStateV1")
    branches: list[BranchStateV1] = Field(default_factory=list)
    evidence_state: EvidenceStateV1
    investigation_budget_id: Id
    active_world_ids: list[Id] = Field(default_factory=list)


class SchedulerDecisionV2(VersionedModel):
    """Branch-aware scheduling output — extends V1 with world/branch ops."""

    SCHEMA_VERSION: ClassVar[str] = "2"
    schema_version: Literal["2"] = "2"

    id: Id = Field(default_factory=new_id)
    task_id: Optional[Id] = None
    world_id: Id
    branch_decision: Optional[str] = Field(
        default=None, description="PRIORITIZE | PRUNE | CONTINUE | TERMINATE_WORLD | ..."
    )
    task_decision: Optional[SchedulerDecisionV1] = None
    scale_out_workers: int = Field(default=0, ge=0)
    scale_in_workers: int = Field(default=0, ge=0)
    allow_speculation: bool = False
    reason_codes: list[ReasonCode] = Field(..., min_length=1)
    estimated_cost_usd: float = Field(default=0, ge=0)
    explanation: str
    created_at: AwareDatetime = Field(default_factory=utc_now)


class InvestigationBudgetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    range_id: Id
    max_total_cost_usd: float = Field(..., gt=0)
    max_runtime_seconds: float = Field(..., gt=0)
    max_worlds: int = Field(default=3, ge=1, le=5)
    max_cpu_workers: int = Field(default=5, ge=0)
    max_gpu_workers: int = Field(default=0, ge=0)
    max_model_cost_usd: float = Field(default=1.0, ge=0)
    reserved_usd: float = Field(default=0, ge=0)
    spent_usd: float = Field(default=0, ge=0)


class HistoricalWorldV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    world_id: Id
    remediation_id: Id
    termination_reason: str
    pruned: bool
    runtime_seconds: float = Field(..., ge=0)
    compute_cost_usd: float = Field(..., ge=0)
    evidence_ids: list[Id] = Field(default_factory=list)
    scheduler_decision_ids: list[Id] = Field(default_factory=list)
    preserved_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = [
    "ForkStrategy",
    "RemediationChangeType",
    "RemediationActionKind",
    "RemediationActionV1",
    "RemediationPlanV1",
    "WorldFingerprintV1",
    "WorldForkV2",
    "AttackReplayActionV1",
    "AttackReplayPlanV1",
    "VerificationSuiteV1",
    "WorldEvaluationV1",
    "BranchStateV1",
    "EvidenceStateV1",
    "SchedulingContextV2",
    "SchedulerDecisionV2",
    "InvestigationBudgetV1",
    "HistoricalWorldV1",
]
