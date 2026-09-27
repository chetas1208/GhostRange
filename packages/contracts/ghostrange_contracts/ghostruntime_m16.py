"""M16 GhostRuntime — durable campaign execution substrate (not a new intelligence layer).

Guarantee target (honest): at-least-once effects with idempotent commit → effectively-once outcomes.
Do NOT claim exactly-once execution without proof.
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Literal, Optional

from pydantic import Field, model_validator

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class CampaignRuntimeState(str, Enum):
    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    RECOVERING = "RECOVERING"
    RECONCILING = "RECONCILING"
    RESUMING = "RESUMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    DEGRADED = "DEGRADED"


class SideEffectStatus(str, Enum):
    INTENDED = "INTENDED"
    SUBMITTED = "SUBMITTED"
    OBSERVED = "OBSERVED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"
    COMPENSATED = "COMPENSATED"


class FailureDomain(str, Enum):
    MODEL = "MODEL"
    CONTROL_PROCESS = "CONTROL_PROCESS"
    CONTROL_VM = "CONTROL_VM"
    DATABASE = "DATABASE"
    OBJECT_STORAGE = "OBJECT_STORAGE"
    NETWORK = "NETWORK"
    VULTR_API = "VULTR_API"
    WORKER = "WORKER"
    TASK = "TASK"
    EVENT_STREAM = "EVENT_STREAM"
    FRONTEND = "FRONTEND"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    INVALID_STATE = "INVALID_STATE"
    OPERATOR = "OPERATOR"


class FailureSeverity(str, Enum):
    INFO = "INFO"
    DEGRADED = "DEGRADED"
    RECOVERABLE = "RECOVERABLE"
    CAMPAIGN_BLOCKING = "CAMPAIGN_BLOCKING"
    CRITICAL = "CRITICAL"


class CapabilityDegradation(str, Enum):
    FULL = "FULL"
    NO_MESH = "NO_MESH"
    NO_INFERENCE = "NO_INFERENCE"
    NO_OBJECT_UPLOAD = "NO_OBJECT_UPLOAD"
    READ_ONLY = "READ_ONLY"
    SAFE_MODE = "SAFE_MODE"


class RecoveryAction(str, Enum):
    RESUME = "RESUME"
    RETRY_TASK = "RETRY_TASK"
    RESTART_STAGE = "RESTART_STAGE"
    RESTART_CAMPAIGN = "RESTART_CAMPAIGN"
    COMPENSATE_AND_FAIL = "COMPENSATE_AND_FAIL"
    SAFE_MODE = "SAFE_MODE"
    ABORT = "ABORT"


class IdempotencyKeyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    key: str = Field(..., min_length=8, max_length=256)
    scope: str = Field(..., description="e.g. worker.create, task.complete, artifact.upload")
    campaign_id: Id


class FencingTokenV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    token: int = Field(..., ge=1)
    issued_at: AwareDatetime = Field(default_factory=utc_now)
    campaign_id: Id


class CampaignRuntimeLeaseV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id
    runtime_instance_id: str
    fencing_token: FencingTokenV1
    expires_at: AwareDatetime


class SideEffectRecordV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    effect_id: Id = Field(default_factory=new_id)
    idempotency_key: IdempotencyKeyV1
    campaign_id: Id
    operation: str
    target: str
    intent_revision: int = Field(..., ge=0)
    status: SideEffectStatus = SideEffectStatus.INTENDED
    requested_at: AwareDatetime = Field(default_factory=utc_now)
    provider_reference: Optional[str] = None
    completed_at: Optional[AwareDatetime] = None
    failure_detail: Optional[str] = None
    reconciliation_state: Optional[str] = None


class CanonicalCampaignStateV1(VersionedModel):
    """Single durable source of truth for a campaign (PostgreSQL authoritative)."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id
    range_id: Id
    runtime_revision: int = Field(default=0, ge=0)
    lifecycle: CampaignRuntimeState = CampaignRuntimeState.CREATED
    degradation: CapabilityDegradation = CapabilityDegradation.FULL
    director_revision: int = Field(default=0, ge=0)
    scheduler_revision: int = Field(default=0, ge=0)
    causal_revision: int = Field(default=0, ge=0)
    dag_revision: int = Field(default=0, ge=0)
    budget_spent_usd: float = Field(default=0.0, ge=0)
    budget_hard_cap_usd: float = Field(..., ge=0)
    pending_side_effect_ids: list[Id] = Field(default_factory=list)
    active_worker_ids: list[Id] = Field(default_factory=list)
    last_checkpoint_id: Optional[Id] = None
    safe_mode: bool = False
    updated_at: AwareDatetime = Field(default_factory=utc_now)


class CampaignCheckpointV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    checkpoint_id: Id = Field(default_factory=new_id)
    campaign_id: Id
    runtime_revision: int = Field(..., ge=0)
    created_at: AwareDatetime = Field(default_factory=utc_now)
    state_digest_sha256: str = Field(..., min_length=64, max_length=64)
    state_blob_ref: Optional[str] = Field(
        default=None, description="Object Storage key for large checkpoint payload"
    )
    inline_state: Optional[dict] = Field(
        default=None, description="Small campaigns may inline JSON state"
    )
    artifact_refs: list[str] = Field(default_factory=list)


class TaskAttemptV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    attempt_id: Id = Field(default_factory=new_id)
    task_id: Id
    campaign_id: Id
    worker_id: Optional[Id] = None
    attempt_number: int = Field(..., ge=1)
    speculative: bool = False
    started_at: Optional[AwareDatetime] = None
    completed_at: Optional[AwareDatetime] = None
    status: str = "PENDING"


class CanonicalTaskResultV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    task_id: Id
    campaign_id: Id
    canonical_attempt_id: Id
    artifact_id: Optional[Id] = None
    result_digest_sha256: Optional[str] = None
    committed_at: AwareDatetime = Field(default_factory=utc_now)


class CompensationActionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    compensation_id: Id = Field(default_factory=new_id)
    effect_id: Id
    action: str
    status: SideEffectStatus = SideEffectStatus.INTENDED
    non_compensatable: bool = False


class RetryBudgetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id
    service: str
    max_attempts: int = Field(..., ge=0)
    attempts_used: int = Field(default=0, ge=0)


class ReliabilityBudgetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id
    dependent_step_count: int = Field(default=0, ge=0)
    observed_step_successes: int = Field(default=0, ge=0)
    retries: int = Field(default=0, ge=0)
    recovered_failures: int = Field(default=0, ge=0)
    unrecovered_failures: int = Field(default=0, ge=0)


class RecoveryDecisionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    decision_id: Id = Field(default_factory=new_id)
    campaign_id: Id
    action: RecoveryAction
    reason_codes: list[str] = Field(..., min_length=1)
    decided_at: AwareDatetime = Field(default_factory=utc_now)
    deterministic: bool = True


class RuntimeSafeModeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id
    entered_at: AwareDatetime = Field(default_factory=utc_now)
    reason: str
    block_new_billable_effects: bool = True
    allow_reconciliation: bool = True


class RuntimeInvariant(str, Enum):
    NO_UNOWNED_RESOURCE_TERMINATION = "NO_UNOWNED_RESOURCE_TERMINATION"
    NO_DUPLICATE_CANONICAL_TASK_RESULT = "NO_DUPLICATE_CANONICAL_TASK_RESULT"
    NO_BUDGET_RESET_ON_RESTART = "NO_BUDGET_RESET_ON_RESTART"
    NO_APPROVAL_CREATION_ON_RECOVERY = "NO_APPROVAL_CREATION_ON_RECOVERY"
    NO_LOST_EVIDENCE_REFERENCE = "NO_LOST_EVIDENCE_REFERENCE"
    NO_STALE_LEASE_COMMIT = "NO_STALE_LEASE_COMMIT"
    NO_ORPHAN_AFTER_FINALIZATION = "NO_ORPHAN_AFTER_FINALIZATION"


class RuntimeCommandV1(VersionedModel):
    """Intent — not a completed effect."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    command_id: Id = Field(default_factory=new_id)
    campaign_id: Id
    name: str
    payload: dict = Field(default_factory=dict)
    idempotency_key: IdempotencyKeyV1
    issued_at: AwareDatetime = Field(default_factory=utc_now)


class RuntimeEventV1(VersionedModel):
    """Observed fact — append-only."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    event_id: Id = Field(default_factory=new_id)
    campaign_id: Id
    aggregate_id: Id
    sequence: int = Field(..., ge=0)
    event_type: str
    payload: dict = Field(default_factory=dict)
    occurred_at: AwareDatetime = Field(default_factory=utc_now)
    schema_version_event: str = "1"


class DeterministicRuntimeReplayV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id
    from_sequence: int = Field(..., ge=0)
    to_sequence: int = Field(..., ge=0)
    replay_policy_version: str = "ghostruntime/replay/v1"
    model_outputs_frozen: bool = True

    @model_validator(mode="after")
    def _seq_order(self) -> "DeterministicRuntimeReplayV1":
        if self.to_sequence < self.from_sequence:
            raise ValueError("to_sequence must be >= from_sequence")
        return self


__all__ = [
    "CampaignCheckpointV1",
    "CampaignRuntimeLeaseV1",
    "CampaignRuntimeState",
    "CanonicalCampaignStateV1",
    "CanonicalTaskResultV1",
    "CapabilityDegradation",
    "CompensationActionV1",
    "DeterministicRuntimeReplayV1",
    "FailureDomain",
    "FailureSeverity",
    "FencingTokenV1",
    "IdempotencyKeyV1",
    "RecoveryAction",
    "RecoveryDecisionV1",
    "ReliabilityBudgetV1",
    "RetryBudgetV1",
    "RuntimeCommandV1",
    "RuntimeEventV1",
    "RuntimeInvariant",
    "RuntimeSafeModeV1",
    "SideEffectRecordV1",
    "SideEffectStatus",
    "TaskAttemptV1",
]
