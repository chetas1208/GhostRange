"""M13 GhostMesh — privacy-preserving federated defensive knowledge (not raw evidence)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class KnowledgeClass(str, Enum):
    COUNTEREXAMPLE_PATTERN = "COUNTEREXAMPLE_PATTERN"
    REMEDIATION_PATTERN = "REMEDIATION_PATTERN"
    VERIFICATION_TEMPLATE = "VERIFICATION_TEMPLATE"
    EXPERIMENT_TEMPLATE = "EXPERIMENT_TEMPLATE"
    SEARCH_PRIOR = "SEARCH_PRIOR"
    SCHEDULER_PRIOR = "SCHEDULER_PRIOR"
    FAILURE_PATTERN = "FAILURE_PATTERN"
    ROLLBACK_PATTERN = "ROLLBACK_PATTERN"
    PRODUCTION_SURPRISE_PATTERN = "PRODUCTION_SURPRISE_PATTERN"
    FIDELITY_LESSON = "FIDELITY_LESSON"


class MeshDisclosureLevel(str, Enum):
    PRIVATE_LOCAL = "PRIVATE_LOCAL"
    FEDERATED_AGGREGATE_ONLY = "FEDERATED_AGGREGATE_ONLY"
    PSEUDONYMOUS_STRUCTURED = "PSEUDONYMOUS_STRUCTURED"
    TRUSTED_GROUP = "TRUSTED_GROUP"
    PUBLIC_SAFE = "PUBLIC_SAFE"


class ApplicabilityResult(str, Enum):
    APPLICABLE = "APPLICABLE"
    POSSIBLY_APPLICABLE = "POSSIBLY_APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class RemoteKnowledgeStatus(str, Enum):
    UNSEEN = "UNSEEN"
    ELIGIBLE = "ELIGIBLE"
    LOCALLY_TESTING = "LOCALLY_TESTING"
    LOCALLY_SUPPORTED = "LOCALLY_SUPPORTED"
    LOCALLY_REJECTED = "LOCALLY_REJECTED"
    STALE = "STALE"
    REVOKED = "REVOKED"
    QUARANTINED = "QUARANTINED"


class MeshProtocolMessageKind(str, Enum):
    CONTRIBUTION = "CONTRIBUTION"
    AGGREGATE = "AGGREGATE"
    REVOCATION = "REVOCATION"
    SCHEMA = "SCHEMA"
    RECEIPT = "RECEIPT"
    MEMBERSHIP = "MEMBERSHIP"
    HEARTBEAT = "HEARTBEAT"


class KnowledgeAbstractionV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    abstract_tags: list[str] = Field(default_factory=list)
    abstract_relations: list[str] = Field(default_factory=list)
    notes: str = ""


class ApplicabilityProfileV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    architecture_family: Optional[str] = None
    protocol: Optional[str] = None
    identity_pattern: Optional[str] = None
    statefulness: Optional[str] = None
    dependency_type: Optional[str] = None
    deployment_model: Optional[str] = None
    runtime_class: Optional[str] = None


class ContributionPrivacyProfileV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    fields_removed: list[str] = Field(default_factory=list)
    fields_generalized: list[str] = Field(default_factory=list)
    fields_hashed: list[str] = Field(default_factory=list)
    dp_applied: bool = False
    aggregation_required: bool = False
    minimum_cohort: int = 1
    residual_leakage_assessment: str = "UNEVALUATED"


class PrivacyBudgetV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    epsilon: float = 0.0
    delta: float = 0.0
    mechanism: str = ""
    scope: str = ""
    consumed: float = 0.0


class MeshContributionPolicyV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    sharing_enabled: bool = False
    allowed_knowledge_classes: list[KnowledgeClass] = Field(default_factory=list)
    minimum_local_validations: int = 1
    minimum_abstraction_tags: int = 2
    default_disclosure: MeshDisclosureLevel = MeshDisclosureLevel.PRIVATE_LOCAL
    require_human_approval: bool = True
    allowed_federation_ids: list[str] = Field(default_factory=list)
    retention_days: int = 90


class KnowledgeFingerprintV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    fingerprint: str
    knowledge_class: KnowledgeClass
    abstract_pattern_hash: str


class MeshContributionV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    id: Id = Field(default_factory=new_id)
    knowledge_class: KnowledgeClass
    abstract_pattern: KnowledgeAbstractionV1
    applicability: ApplicabilityProfileV1 = Field(default_factory=ApplicabilityProfileV1)
    evidence_strength: float = Field(ge=0.0, le=1.0, default=0.5)
    local_validation_count: int = 0
    failure_count: int = 0
    provenance_digest: str
    privacy_profile: ContributionPrivacyProfileV1 = Field(default_factory=ContributionPrivacyProfileV1)
    disclosure_level: MeshDisclosureLevel = MeshDisclosureLevel.PSEUDONYMOUS_STRUCTURED
    contributor_pseudonym: str = ""
    created_at: AwareDatetime = Field(default_factory=utc_now)
    expires_at: Optional[AwareDatetime] = None
    revocation_reference: Optional[str] = None
    content_digest: str = ""


class MeshNodeIdentityV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    node_id: str
    public_key_fingerprint: str
    federation_ids: list[str] = Field(default_factory=list)
    display_pseudonym: str = ""


class MeshFederationV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    federation_id: str
    policy_digest: str = ""
    trust_root_fingerprints: list[str] = Field(default_factory=list)
    accepted_schemas: list[str] = Field(default_factory=lambda: ["MeshContributionV1"])
    accepted_disclosure_levels: list[MeshDisclosureLevel] = Field(default_factory=list)
    minimum_cohort_release: int = 3
    privacy_requirements_digest: str = ""


class GhostMeshProtocolEnvelopeV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    protocol_version: str = "GhostMeshProtocolV1"
    message_kind: MeshProtocolMessageKind
    federation_id: str
    sender_node_id: str
    message_id: str
    sent_at: AwareDatetime = Field(default_factory=utc_now)
    payload_digest: str
    signature: str = ""


class AggregatedKnowledgeV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    aggregate_id: Id = Field(default_factory=new_id)
    knowledge_class: KnowledgeClass
    abstract_summary: KnowledgeAbstractionV1
    contributor_cohort_size: int
    cohort_bucket_label: str = ""
    validation_success_rate: float = 0.0
    privacy_profile: ContributionPrivacyProfileV1 = Field(default_factory=ContributionPrivacyProfileV1)


class ContributionQualityV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    contribution_id: Id
    provenance_valid: bool = False
    local_validations: int = 0
    cross_node_validations: int = 0
    recency_score: float = 0.0
    schema_compatible: bool = True
    poisoning_signals: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class ContributionAnomalyV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    contribution_id: Id
    anomaly_kind: str
    severity: str
    reason_codes: list[str] = Field(default_factory=list)


class ContributionRevocationV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    contribution_id: Id
    revoked_at: AwareDatetime = Field(default_factory=utc_now)
    revoker_node_id: str
    reason: str = ""


class MeshPriorV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    prior_id: Id = Field(default_factory=new_id)
    source_contribution_id: Id
    knowledge_class: KnowledgeClass
    abstract_tags: list[str] = Field(default_factory=list)
    applicability_hint: str = ""
    support_label: str = "AGGREGATED"
    exploration_weight: float = Field(default=0.25, ge=0.0, le=1.0)


class MeshReceiptV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    receipt_id: Id = Field(default_factory=new_id)
    contribution_digest: str
    received_at: AwareDatetime = Field(default_factory=utc_now)
    verifying_node_id: str
    policy_digest: str
    local_decision: RemoteKnowledgeStatus


class KnowledgeUtilityReportV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    node_id: str
    contribution_id: Optional[Id] = None
    experiments_reordered: int = 0
    compute_usd_saved_estimate: float = 0.0
    decision_changed: bool = False
    local_validation_result: Optional[str] = None


class NegativeTransferV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    contribution_id: Id
    wasted_experiments: int = 0
    wasted_compute_usd: float = 0.0
    reason: str = ""


class GhostMeshThreatModelV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    coordinator_trust: str = "HONEST_BUT_CURIOUS"
    participant_trust: str = "BYZANTINE_POSSIBLE"
    adversaries: list[str] = Field(
        default_factory=lambda: [
            "malicious_coordinator",
            "malicious_participant",
            "sybil",
            "poisoning_contributor",
            "membership_inference",
            "contribution_reconstruction",
            "replay",
        ]
    )
    out_of_scope: list[str] = Field(default_factory=lambda: ["physical_access", "side_channel"])


class LocalNormalizedGraphV1(VersionedModel):
    """Privacy-safe local features for applicability — no hostnames."""

    schema_version: Literal["1"] = "1"
    tags: list[str] = Field(default_factory=list)
    capability_flags: dict[str, bool] = Field(default_factory=dict)


class ApplicabilityReportV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    contribution_id: Id
    result: ApplicabilityResult
    matched_tags: list[str] = Field(default_factory=list)
    explanation: str = ""


class FederatedPriorModelV1(VersionedModel):
    """Experimental — ranks what to test; never security claims."""

    schema_version: Literal["1"] = "1"
    model_id: str
    feature_schema_version: str = "1"
    training_round: int = 0
    rank_weights: dict[str, float] = Field(default_factory=dict)


class MeshCandidateKnowledgeV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    candidate_id: Id = Field(default_factory=new_id)
    knowledge_class: KnowledgeClass
    local_source_ref: str
    raw_internal_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: AwareDatetime = Field(default_factory=utc_now)
