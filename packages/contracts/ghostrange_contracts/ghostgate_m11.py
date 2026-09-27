"""M11 GhostGate — human-controlled promotion, no production mutation."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class PromotionState(str, Enum):
    DRAFT = "DRAFT"
    ASSESSING = "ASSESSING"
    REQUIRES_RETEST = "REQUIRES_RETEST"
    REQUIRES_REVALIDATION = "REQUIRES_REVALIDATION"
    ROLLBACK_TESTING = "ROLLBACK_TESTING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"


class EquivalenceStatus(str, Enum):
    EXACT = "EXACT"
    FUNCTIONALLY_EQUIVALENT = "FUNCTIONALLY_EQUIVALENT"
    MATERIAL_DIFFERENCE = "MATERIAL_DIFFERENCE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    UNKNOWN = "UNKNOWN"


class EquivalenceDimension(str, Enum):
    CONFIGURATION = "CONFIGURATION"
    SERVICE_VERSION = "SERVICE_VERSION"
    IMAGE = "IMAGE"
    DEPENDENCY = "DEPENDENCY"
    NETWORK = "NETWORK"
    IDENTITY = "IDENTITY"
    DATA_SCHEMA = "DATA_SCHEMA"
    RESOURCE = "RESOURCE"
    ROLLBACK_BEHAVIOR = "ROLLBACK_BEHAVIOR"


class ReadinessDimensionStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RiskLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class DeploymentStrategyKind(str, Enum):
    ALL_AT_ONCE = "ALL_AT_ONCE"
    CANARY = "CANARY"
    BLUE_GREEN = "BLUE_GREEN"
    ROLLING = "ROLLING"
    SHADOW = "SHADOW"
    CONFIG_FLAG = "CONFIG_FLAG"
    MANUAL_SEQUENCE = "MANUAL_SEQUENCE"


class RollbackStatus(str, Enum):
    UNTESTED = "UNTESTED"
    TESTED_PASS = "TESTED_PASS"
    TESTED_FAIL = "TESTED_FAIL"
    PARTIAL = "PARTIAL"
    IRREVERSIBLE = "IRREVERSIBLE"


class ApprovalDecisionKind(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


class ChangeActionKind(str, Enum):
    CONFIG = "CONFIG"
    CONTAINER_IMAGE = "CONTAINER_IMAGE"
    PACKAGE_VERSION = "PACKAGE_VERSION"
    INFRA_PARAMETER = "INFRA_PARAMETER"
    NETWORK_POLICY = "NETWORK_POLICY"
    IDENTITY_POLICY = "IDENTITY_POLICY"
    DATABASE_MIGRATION_REF = "DATABASE_MIGRATION_REF"


class BundleMode(str, Enum):
    INTERNAL_FULL = "INTERNAL_FULL"
    REVIEW_REDACTED = "REVIEW_REDACTED"
    CI_ARTIFACT = "CI_ARTIFACT"


class ChangeActionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    kind: ChangeActionKind
    target_path: str
    description: str
    before_summary: str = ""
    after_summary: str = ""
    remediation_ref: Optional[str] = None


class TestedProductionDeltaV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    tested_actions: list[ChangeActionV1] = Field(default_factory=list)
    proposed_actions: list[ChangeActionV1] = Field(default_factory=list)
    tested_patch_digest: str
    proposed_patch_digest: str


class ChangeEquivalenceReportV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    dimensions: dict[str, EquivalenceStatus] = Field(default_factory=dict)
    overall: EquivalenceStatus = EquivalenceStatus.UNKNOWN
    notes: list[str] = Field(default_factory=list)


class PromotionReadinessV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    claim_validity: ReadinessDimensionStatus = ReadinessDimensionStatus.SKIP
    fidelity: ReadinessDimensionStatus = ReadinessDimensionStatus.SKIP
    change_equivalence: ReadinessDimensionStatus = ReadinessDimensionStatus.SKIP
    source_currency: ReadinessDimensionStatus = ReadinessDimensionStatus.SKIP
    regression_status: ReadinessDimensionStatus = ReadinessDimensionStatus.SKIP
    adversarial_status: ReadinessDimensionStatus = ReadinessDimensionStatus.SKIP
    rollback_readiness: ReadinessDimensionStatus = ReadinessDimensionStatus.SKIP
    observability_readiness: ReadinessDimensionStatus = ReadinessDimensionStatus.SKIP
    approval_readiness: ReadinessDimensionStatus = ReadinessDimensionStatus.SKIP
    residual_uncertainty: ReadinessDimensionStatus = ReadinessDimensionStatus.SKIP
    blockers: list[str] = Field(default_factory=list)


class ChangeRiskProfileV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    blast_radius: RiskLevel = RiskLevel.MEDIUM
    statefulness: RiskLevel = RiskLevel.LOW
    reversibility: RiskLevel = RiskLevel.MEDIUM
    dependency_depth: RiskLevel = RiskLevel.LOW
    data_impact: RiskLevel = RiskLevel.NONE
    identity_impact: RiskLevel = RiskLevel.HIGH
    network_impact: RiskLevel = RiskLevel.LOW
    availability_risk: RiskLevel = RiskLevel.MEDIUM
    rollback_complexity: RiskLevel = RiskLevel.LOW
    observability_gap: RiskLevel = RiskLevel.LOW
    affected_component_ids: list[str] = Field(default_factory=list)


class CanaryStageV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    stage_index: int = Field(..., ge=0)
    traffic_percentage: float = Field(..., ge=0, le=100)
    duration_minutes: int = Field(..., ge=1)
    success_conditions: list[str] = Field(default_factory=list)
    failure_conditions: list[str] = Field(default_factory=list)


class CanaryPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    stages: list[CanaryStageV1] = Field(default_factory=list)
    rollback_trigger: list[str] = Field(default_factory=list)
    note: str = "PLAN ONLY — not production traffic routing"


class DeploymentStrategyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    kind: DeploymentStrategyKind
    rationale: str = ""
    canary: Optional[CanaryPlanV1] = None


class RollbackPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    rollback_type: str = "CONFIG_REVERT"
    steps: list[str] = Field(default_factory=list)
    required_artifacts: list[str] = Field(default_factory=list)
    estimated_duration_minutes: int = 15
    data_reversibility: str = "FULL"
    verification: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class PostDeploymentVerificationPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    health_checks: list[str] = Field(default_factory=list)
    security_regressions: list[str] = Field(default_factory=list)
    behavioral_invariants: list[str] = Field(default_factory=list)
    rollback_triggers: list[str] = Field(default_factory=list)


class ObservabilityRequirementV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    signals: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class ResidualRiskV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    description: str
    category: str = "UNCERTAINTY"
    severity: str = "MEDIUM"


class ProductionChangeCandidateV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    remediation_id: Id
    remediation_revision_label: str = "Fix B.2"
    source_revision_id: Id
    twin_revision_id: Id
    experiment_id: Id
    claim_ids: list[Id] = Field(default_factory=list)
    evidence_root_digest: str
    target_environment_class: str = "PRODUCTION_CANDIDATE"
    affected_components: list[str] = Field(default_factory=list)
    change_actions: list[ChangeActionV1] = Field(default_factory=list)
    tested_delta: Optional[TestedProductionDeltaV1] = None
    equivalence: Optional[ChangeEquivalenceReportV1] = None
    readiness: PromotionReadinessV1 = Field(default_factory=PromotionReadinessV1)
    risk: Optional[ChangeRiskProfileV1] = None
    deployment_strategy: Optional[DeploymentStrategyV1] = None
    rollback_plan: Optional[RollbackPlanV1] = None
    rollback_status: RollbackStatus = RollbackStatus.UNTESTED
    post_change_verification: Optional[PostDeploymentVerificationPlanV1] = None
    observability: Optional[ObservabilityRequirementV1] = None
    residual_risks: list[ResidualRiskV1] = Field(default_factory=list)
    patch_text: str = ""
    change_candidate_hash: str = ""
    state: PromotionState = PromotionState.DRAFT
    adversarial_summary: str = ""
    known_limitations: list[str] = Field(default_factory=list)
    created_at: AwareDatetime = Field(default_factory=utc_now)


class ApprovalPolicyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    required_approvals: int = Field(1, ge=1)
    identity_change_requires: int = Field(2, ge=1)
    database_change_requires: int = Field(2, ge=1)


class ApprovalRequestV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    change_candidate_id: Id
    change_candidate_hash: str
    summary: str
    required_approvals: int = 1
    created_at: AwareDatetime = Field(default_factory=utc_now)
    expires_at: Optional[AwareDatetime] = None


class ApprovalDecisionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    request_id: Id
    change_candidate_hash: str
    decision: ApprovalDecisionKind
    approver_id: str = Field(..., description="Human/service identity — never MODEL")
    approver_kind: Literal["HUMAN", "SERVICE"] = "HUMAN"
    rationale: str = ""
    decided_at: AwareDatetime = Field(default_factory=utc_now)


class PromotionAttestationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    experiment_root_digest: str
    change_candidate_hash: str
    predicate_type: str = "https://ghostrange.local/attestation/promotion/v1"
    note: str = "Integrity/lineage only — not production safety"


class GhostPromotionBundleV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    mode: BundleMode
    candidate: ProductionChangeCandidateV1
    approval_request: Optional[ApprovalRequestV1] = None
    approval_decisions: list[ApprovalDecisionV1] = Field(default_factory=list)
    attestation: Optional[PromotionAttestationV1] = None
    bundle_digest: Optional[str] = None


__all__ = [
    "PromotionState",
    "ProductionChangeCandidateV1",
    "TestedProductionDeltaV1",
    "ChangeEquivalenceReportV1",
    "PromotionReadinessV1",
    "ChangeRiskProfileV1",
    "DeploymentStrategyV1",
    "CanaryPlanV1",
    "RollbackPlanV1",
    "PostDeploymentVerificationPlanV1",
    "ObservabilityRequirementV1",
    "ApprovalRequestV1",
    "ApprovalDecisionV1",
    "ApprovalPolicyV1",
    "GhostPromotionBundleV1",
    "PromotionAttestationV1",
]
