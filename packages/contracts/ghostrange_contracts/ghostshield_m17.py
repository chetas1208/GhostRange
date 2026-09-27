"""M17 GhostShield — typed actions, policy, permits (not LLM safety)."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class TrustClass(str, Enum):
    TRUSTED = "TRUSTED"
    SEMI_TRUSTED = "SEMI_TRUSTED"
    UNTRUSTED = "UNTRUSTED"


class GhostShieldMode(str, Enum):
    DISABLED = "DISABLED"
    SHADOW = "SHADOW"
    ENFORCE = "ENFORCE"
    LOCKDOWN = "LOCKDOWN"


class CanonicalActionType(str, Enum):
    CREATE_WORKER = "CREATE_WORKER"
    TERMINATE_WORKER = "TERMINATE_WORKER"
    CREATE_WORLD = "CREATE_WORLD"
    DESTROY_WORLD = "DESTROY_WORLD"
    START_EXPERIMENT = "START_EXPERIMENT"
    EXECUTE_RANGE_TASK = "EXECUTE_RANGE_TASK"
    UPLOAD_EVIDENCE = "UPLOAD_EVIDENCE"
    ADVANCE_ROLLOUT = "ADVANCE_ROLLOUT"
    PAUSE_ROLLOUT = "PAUSE_ROLLOUT"
    ROLLBACK = "ROLLBACK"
    PUBLISH_MESH_CONTRIBUTION = "PUBLISH_MESH_CONTRIBUTION"
    PROMOTE_EVOLUTION_CANDIDATE = "PROMOTE_EVOLUTION_CANDIDATE"
    INFERENCE_WORKER_CALL = "INFERENCE_WORKER_CALL"


class AuthorizationVerdict(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    HOLD = "HOLD"
    REQUIRE_HUMAN = "REQUIRE_HUMAN"
    STATE_STALE = "STATE_STALE"
    POLICY_ERROR = "POLICY_ERROR"


class PolicyKind(str, Enum):
    PRECONDITION = "PRECONDITION"
    INVARIANT = "INVARIANT"
    ACTION_CONSTRAINT = "ACTION_CONSTRAINT"
    TEMPORAL_CONSTRAINT = "TEMPORAL_CONSTRAINT"
    BUDGET_CONSTRAINT = "BUDGET_CONSTRAINT"
    OWNERSHIP_CONSTRAINT = "OWNERSHIP_CONSTRAINT"
    APPROVAL_CONSTRAINT = "APPROVAL_CONSTRAINT"
    POSTCONDITION = "POSTCONDITION"
    OBLIGATION = "OBLIGATION"


class AssuranceLevel(str, Enum):
    MODEL_CHECKED = "MODEL_CHECKED"
    RUNTIME_ENFORCED = "RUNTIME_ENFORCED"
    RUNTIME_MONITORED = "RUNTIME_MONITORED"
    TESTED_ONLY = "TESTED_ONLY"
    NOT_COVERED = "NOT_COVERED"


class GhostShieldTrustModelV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    llm: TrustClass = TrustClass.UNTRUSTED
    director: TrustClass = TrustClass.UNTRUSTED
    scheduler: TrustClass = TrustClass.UNTRUSTED
    frontend: TrustClass = TrustClass.UNTRUSTED
    worker: TrustClass = TrustClass.SEMI_TRUSTED
    mesh_remote: TrustClass = TrustClass.UNTRUSTED
    policy_engine: TrustClass = TrustClass.TRUSTED
    canonical_postgres: TrustClass = TrustClass.TRUSTED
    provider_response: TrustClass = TrustClass.SEMI_TRUSTED


class AuthorizationContextV1(VersionedModel):
    """Snapshot inputs for authorization (must match execution-time re-check)."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id
    runtime_revision: int = Field(..., ge=0)
    active_workers: int = Field(..., ge=0)
    max_active_workers: int = Field(..., ge=0)
    budget_spent_usd: float = Field(..., ge=0)
    budget_hard_cap_usd: float = Field(..., ge=0)
    safe_mode: bool = False
    allow_live_gpu: bool = False
    resource_owned: bool = True
    approval_digest: Optional[str] = None


class CanonicalActionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    action_id: Id = Field(default_factory=new_id)
    action_type: CanonicalActionType
    principal: str
    campaign_id: Id
    target: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    state_revision: int = Field(..., ge=0)
    policy_version: str = "ghostshield/v1"
    idempotency_key: str
    issued_at: AwareDatetime = Field(default_factory=utc_now)
    expires_at: Optional[AwareDatetime] = None

    def canonical_digest(self) -> str:
        payload = {
            "action_type": self.action_type.value,
            "principal": self.principal,
            "campaign_id": str(self.campaign_id),
            "target": self.target,
            "parameters": self.parameters,
            "state_revision": self.state_revision,
            "policy_version": self.policy_version,
            "idempotency_key": self.idempotency_key,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


class AuthorizationVerdictV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    verdict: AuthorizationVerdict
    action_digest: str
    reason_codes: list[str] = Field(default_factory=list)
    human_explanation: str = ""
    evaluated_at: AwareDatetime = Field(default_factory=utc_now)
    policy_version: str = "ghostshield/v1"


class ActionPermitV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    permit_id: Id = Field(default_factory=new_id)
    action_digest: str
    principal: str
    policy_version: str
    state_revision: int
    campaign_id: Id
    issued_at: AwareDatetime = Field(default_factory=utc_now)
    expires_at: AwareDatetime
    single_use: bool = True
    consumed: bool = False


class AuthorizationEvidenceV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    evidence_id: Id = Field(default_factory=new_id)
    action_digest: str
    policy_digest_sha256: str
    state_revision: int
    verdict: AuthorizationVerdict
    reason_codes: list[str] = Field(default_factory=list)
    permit_digest_sha256: Optional[str] = None
    execution_observed: Optional[str] = None
    recorded_at: AwareDatetime = Field(default_factory=utc_now)


class RuntimePropertyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    property_id: str
    description: str
    formal_expression: str = ""
    monitor_type: str = "STATE_INVARIANT"
    severity: str = "CRITICAL"
    assurance: AssuranceLevel = AssuranceLevel.NOT_COVERED


class AssuranceCoverageV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    property_id: str
    assurance: AssuranceLevel
    assumptions: list[str] = Field(default_factory=list)


class AgentBehaviorContractV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    component: str
    allowed_actions: list[CanonicalActionType] = Field(default_factory=list)
    forbidden_actions: list[CanonicalActionType] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)


# Hard property IDs (P1–P12 from M17 brief)
HARD_PROPERTIES: dict[str, str] = {
    "P1": "Never terminate an unowned Vultr resource",
    "P2": "Never exceed MAX_ACTIVE_WORKERS",
    "P3": "Never create GPU worker without live-GPU authorization",
    "P11": "No new billable effects in GhostRuntime SAFE_MODE",
}

__all__ = [
    "ActionPermitV1",
    "AgentBehaviorContractV1",
    "AssuranceCoverageV1",
    "AssuranceLevel",
    "AuthorizationContextV1",
    "AuthorizationEvidenceV1",
    "AuthorizationVerdict",
    "AuthorizationVerdictV1",
    "CanonicalActionType",
    "CanonicalActionV1",
    "GhostShieldMode",
    "GhostShieldTrustModelV1",
    "HARD_PROPERTIES",
    "PolicyKind",
    "RuntimePropertyV1",
    "TrustClass",
]
