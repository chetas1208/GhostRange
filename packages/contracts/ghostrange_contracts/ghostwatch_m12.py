"""M12 GhostWatch — post-approval deployment observation (not autonomous prod admin)."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class DeploymentAuthorityMode(str, Enum):
    OBSERVE_ONLY = "OBSERVE_ONLY"
    RECOMMEND = "RECOMMEND"
    PREAUTHORIZED_PAUSE = "PREAUTHORIZED_PAUSE"
    PREAUTHORIZED_ROLLBACK = "PREAUTHORIZED_ROLLBACK"


class ExecutorCapability(str, Enum):
    OBSERVE_STATUS = "OBSERVE_STATUS"
    OBSERVE_REVISION = "OBSERVE_REVISION"
    OBSERVE_STAGE = "OBSERVE_STAGE"
    OBSERVE_HEALTH = "OBSERVE_HEALTH"
    OBSERVE_METRICS = "OBSERVE_METRICS"
    REQUEST_PAUSE = "REQUEST_PAUSE"
    REQUEST_RESUME = "REQUEST_RESUME"
    REQUEST_ROLLBACK = "REQUEST_ROLLBACK"
    REQUEST_PROMOTION = "REQUEST_APPROVED_PROMOTION"


class ConformanceDimension(str, Enum):
    ARTIFACT = "ARTIFACT"
    CONFIGURATION = "CONFIGURATION"
    SERVICE_VERSION = "SERVICE_VERSION"
    NETWORK_POLICY = "NETWORK_POLICY"
    IDENTITY_POLICY = "IDENTITY_POLICY"
    DEPENDENCY = "DEPENDENCY"
    ROLLOUT_STRATEGY = "ROLLOUT_STRATEGY"
    ENVIRONMENT = "ENVIRONMENT"


class ExposureKind(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    REPLICA_FRACTION = "REPLICA_FRACTION"
    COHORT = "COHORT"
    REGION = "REGION"
    FEATURE_FLAG = "FEATURE_FLAG"
    CUSTOM = "CUSTOM"


class DeploymentExecutionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ROLLING_BACK = "ROLLING_BACK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class RolloutStageKind(str, Enum):
    PRE_DEPLOY = "PRE_DEPLOY"
    INITIAL_CANARY = "INITIAL_CANARY"
    CANARY_10 = "CANARY_10"
    CANARY_25 = "CANARY_25"
    CANARY_50 = "CANARY_50"
    FULL = "FULL"
    HOLD = "HOLD"
    ROLLBACK = "ROLLBACK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ConformanceStatus(str, Enum):
    MATCH = "MATCH"
    FUNCTIONALLY_EQUIVALENT = "FUNCTIONALLY_EQUIVALENT"
    MATERIAL_DIFFERENCE = "MATERIAL_DIFFERENCE"
    UNKNOWN = "UNKNOWN"
    NOT_OBSERVABLE = "NOT_OBSERVABLE"


class GateEvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ERROR = "ERROR"


class CanaryAnalysisOutcome(str, Enum):
    ADVANCE = "ADVANCE"  # alias — prefer ADVANCE_RECOMMENDED in new code
    ADVANCE_RECOMMENDED = "ADVANCE_RECOMMENDED"
    HOLD = "HOLD"
    ABORT_RECOMMENDED = "ABORT_RECOMMENDED"
    ROLLBACK_RECOMMENDED = "ROLLBACK_RECOMMENDED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class GhostWatchCampaignState(str, Enum):
    WAITING_FOR_EXTERNAL_DEPLOYMENT = "WAITING_FOR_EXTERNAL_DEPLOYMENT"
    OBSERVING = "OBSERVING"
    VALIDATING_CONFORMANCE = "VALIDATING_CONFORMANCE"
    CANARY_ANALYSIS = "CANARY_ANALYSIS"
    HOLD = "HOLD"
    ADVANCE_RECOMMENDED = "ADVANCE_RECOMMENDED"
    PAUSE_RECOMMENDED = "PAUSE_RECOMMENDED"
    ROLLBACK_RECOMMENDED = "ROLLBACK_RECOMMENDED"
    ROLLBACK_REQUESTED = "ROLLBACK_REQUESTED"
    ROLLBACK_VERIFYING = "ROLLBACK_VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CRITICAL = "CRITICAL"
    SUPERSEDED = "SUPERSEDED"


class DeploymentExecutorCapabilitiesV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    adapter_id: str
    capabilities: list[ExecutorCapability] = Field(default_factory=list)
    environment_label: str = "SIMULATED"


class ObservedDeploymentStateV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    artifact_digest: str = ""
    config_fingerprint: str = ""
    service_version: str = ""
    deployment_revision: str = ""
    infrastructure_fingerprint: str = ""
    traffic_percentage_new: float = Field(0, ge=0, le=100)
    observed_at: AwareDatetime = Field(default_factory=utc_now)
    source: str = "adapter"


class DeploymentConformanceReportV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    approved_artifact_digest: str
    observed_artifact_digest: str
    status: ConformanceStatus = ConformanceStatus.UNKNOWN
    dimensions: dict[str, ConformanceStatus] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ExposureV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    kind: ExposureKind = ExposureKind.PERCENTAGE
    value: str = "0"
    label: str = ""


class ObservationWindowV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    duration_seconds: int = Field(300, ge=1)
    sample_interval_seconds: int = Field(30, ge=1)
    minimum_samples: int = Field(5, ge=1)
    warmup_seconds: int = Field(60, ge=0)


class ApprovedRollbackTargetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    revision: str
    artifact_digest: str
    config_fingerprint: str = ""
    immutable: bool = True


class RollbackExecutionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    trigger_id: str
    authorized: bool
    target: ApprovedRollbackTargetV1
    executor_response: str = ""
    observed_digest_after: str = ""
    verified: bool = False
    result: str = "PENDING"


class GhostWatchPolicyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    version: str = "ghostwatch-v1"
    default_authority: DeploymentAuthorityMode = DeploymentAuthorityMode.OBSERVE_ONLY
    required_conformance_dimensions: list[ConformanceDimension] = Field(
        default_factory=lambda: [ConformanceDimension.ARTIFACT, ConformanceDimension.CONFIGURATION]
    )
    missing_data_policy: str = "HOLD"
    debounce_consecutive_failures: int = 2
    control_fail_closed: bool = True


class TwinPredictionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    promotion_candidate_id: Id
    expected_artifact_digest: str
    expected_behavior_summary: str
    recorded_at: AwareDatetime = Field(default_factory=utc_now)
    note: str = "Immutable — do not rewrite after rollout observation"


class ProductionObservationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id
    observed_state: ObservedDeploymentStateV1
    exposure: Optional[ExposureV1] = None
    recorded_at: AwareDatetime = Field(default_factory=utc_now)


class ObservedSourceStateV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    config_fingerprint: str
    service_version: str
    note: str = "Not auto-committed to Git source-of-truth"


class RolloutStageV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    kind: RolloutStageKind
    traffic_percentage_new: float = Field(0, ge=0, le=100)
    started_at: AwareDatetime = Field(default_factory=utc_now)


class MetricQueryV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    query_id: str
    metric_name: str
    window_seconds: int = Field(300, ge=1)
    min_samples: int = Field(5, ge=1)


class ObservabilityAdapterCapabilitiesV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    adapter_id: str
    metrics: bool = True
    logs: bool = False
    traces: bool = False
    health: bool = True


class RuntimeInvariantV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    invariant_id: str
    promotion_id: Optional[Id] = None
    observable: str
    evaluation: str
    window_seconds: int = 300
    severity: str = "HIGH"
    required: bool = True
    failure_action: str = "HOLD"
    consecutive_failures_required: int = Field(2, ge=1)


class SyntheticTransactionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    transaction_id: str
    description: str
    endpoint: str
    method: str = "GET"
    synthetic_identity: str = "ghostwatch-synthetic@internal"
    rate_limit_per_minute: int = Field(10, ge=1)
    read_only: bool = True


class RuntimeBaselineV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    period_label: str
    service_version: str
    error_rate_max: float = 0.01
    latency_p95_ms_max: float = 500.0
    auth_denial_rate_min: float = 0.0


class StageGateV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    gate_id: str
    requires_conformance: ConformanceStatus = ConformanceStatus.MATCH
    requires_health: GateEvaluationStatus = GateEvaluationStatus.PASS
    requires_security_invariant: GateEvaluationStatus = GateEvaluationStatus.PASS
    requires_error_rate: GateEvaluationStatus = GateEvaluationStatus.PASS
    requires_latency: GateEvaluationStatus = GateEvaluationStatus.PASS


class CanaryAnalysisV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    stage: RolloutStageKind
    outcome: CanaryAnalysisOutcome
    gate_results: dict[str, GateEvaluationStatus] = Field(default_factory=dict)
    rationale_codes: list[str] = Field(default_factory=list)
    analyzed_at: AwareDatetime = Field(default_factory=utc_now)


class RollbackTriggerV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    trigger_id: str
    condition: str
    debounce_windows: int = 2
    immediate_on_critical: bool = True


class ProductionEvidenceV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    kind: str
    content_hash: str
    reference: str = ""
    redacted_summary: str = ""
    recorded_at: AwareDatetime = Field(default_factory=utc_now)


class ProductionSurpriseV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    description: str
    twin_expectation: str
    production_observation: str
    severity: str = "MEDIUM"
    detected_at: AwareDatetime = Field(default_factory=utc_now)


class DeploymentObservationAttestationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    approved_change_hash: str
    observed_artifact_digest: str
    campaign_id: Id
    note: str = "Observation integrity — not production safety proof"


class DeploymentExecutionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    promotion_candidate_id: Id
    approval_decision_id: Id
    approved_change_hash: str
    approved_source_revision: str = ""
    approved_strategy_hash: str = ""
    approved_rollback_hash: str = ""
    executor: str = "mock"
    executor_type: str = "mock"
    executor_execution_id: str = ""
    executor_revision_id: str = ""
    environment_reference: str = "SIMULATED_ROLLOUT"
    started_at: AwareDatetime = Field(default_factory=utc_now)
    observed_at: Optional[AwareDatetime] = None
    current_stage: RolloutStageKind = RolloutStageKind.PRE_DEPLOY
    current_exposure: Optional[ExposureV1] = None
    observed_artifact_versions: list[str] = Field(default_factory=list)
    status: DeploymentExecutionStatus = DeploymentExecutionStatus.PENDING
    authority_mode: DeploymentAuthorityMode = DeploymentAuthorityMode.OBSERVE_ONLY
    correlation_id: str = ""


class GhostWatchCampaignV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    promotion_candidate_id: Id
    approval_decision_id: Id
    execution: DeploymentExecutionV1
    state: GhostWatchCampaignState = GhostWatchCampaignState.WAITING_FOR_EXTERNAL_DEPLOYMENT
    policy_version: str = "ghostwatch-v1"
    twin_prediction: Optional[TwinPredictionV1] = None
    approved_artifact_digest: str = ""
    rollback_target: Optional[ApprovedRollbackTargetV1] = None
    conformance: Optional[DeploymentConformanceReportV1] = None
    current_analysis: Optional[CanaryAnalysisV1] = None
    evidence_ids: list[Id] = Field(default_factory=list)
    rollback_state: Optional[RollbackExecutionV1] = None
    control_disabled: bool = False
    event_sequence: int = 0
    created_at: AwareDatetime = Field(default_factory=utc_now)
    updated_at: AwareDatetime = Field(default_factory=utc_now)


class ExternalDeploymentRecordV1(VersionedModel):
    """Ingress from external deployment executor (signed webhook / manual adapter)."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    executor: str
    external_id: str
    campaign_id: Optional[Id] = None
    approved_change_hash: str = ""
    event_id: str = ""
    sequence: int = Field(0, ge=0)
    signature: str = ""
    observed_state: ObservedDeploymentStateV1
    stage: Optional[RolloutStageKind] = None
    exposure: Optional[ExposureV1] = None
    recorded_at: AwareDatetime = Field(default_factory=utc_now)
