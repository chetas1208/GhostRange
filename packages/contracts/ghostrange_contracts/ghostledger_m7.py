"""M7 GhostLedger — experiment provenance, attestation, bundles, replay."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class ReplayLevel(str, Enum):
    LEVEL_0 = "LEVEL_0"
    LEVEL_1 = "LEVEL_1"
    LEVEL_2 = "LEVEL_2"
    LEVEL_3 = "LEVEL_3"
    LEVEL_4 = "LEVEL_4"
    LEVEL_5 = "LEVEL_5"


class DisclosureLevel(str, Enum):
    PRIVATE = "PRIVATE"
    INTERNAL = "INTERNAL"
    SHAREABLE_REDACTED = "SHAREABLE_REDACTED"
    PUBLIC_DIGEST_ONLY = "PUBLIC_DIGEST_ONLY"


class BundleMode(str, Enum):
    FULL = "FULL"
    THIN = "THIN"
    REDACTED = "REDACTED"


class TransparencyLogMode(str, Enum):
    OFF = "OFF"
    LOCAL = "LOCAL"
    PUBLIC_DIGEST_ONLY = "PUBLIC_DIGEST_ONLY"


class SigningIdentityKind(str, Enum):
    LOCAL_DEVELOPMENT = "LOCAL_DEVELOPMENT"
    IDENTITY_BOUND = "IDENTITY_BOUND"


class PromptDisclosure(str, Enum):
    HASH_ONLY = "HASH_ONLY"
    REDACTED = "REDACTED"
    FULL_AUTHORIZED = "FULL_AUTHORIZED"


class ProvenanceNodeKind(str, Enum):
    SOURCE_REVISION = "SOURCE_REVISION"
    TWIN_REVISION = "TWIN_REVISION"
    EXPERIMENT = "EXPERIMENT"
    WORLD = "WORLD"
    TASK = "TASK"
    SCHEDULER_DECISION = "SCHEDULER_DECISION"
    MODEL_INVOCATION = "MODEL_INVOCATION"
    TOOL_INVOCATION = "TOOL_INVOCATION"
    EVIDENCE_ARTIFACT = "EVIDENCE_ARTIFACT"
    VERIFICATION = "VERIFICATION"
    CLAIM = "CLAIM"
    ATTESTATION = "ATTESTATION"


class ProvenanceEdgeKind(str, Enum):
    DERIVED_FROM = "DERIVED_FROM"
    GENERATED_BY = "GENERATED_BY"
    USED = "USED"
    EXECUTED_IN = "EXECUTED_IN"
    SUPPORTED_BY = "SUPPORTED_BY"
    SUPERSEDES = "SUPERSEDES"
    REVALIDATES = "REVALIDATES"
    FORKED_FROM = "FORKED_FROM"
    SCHEDULED_BY = "SCHEDULED_BY"
    ATTESTED_BY = "ATTESTED_BY"


class VerificationDimensionStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ReplayEquivalence(str, Enum):
    EXACT = "EXACT"
    SEMANTICALLY_EQUIVALENT = "SEMANTICALLY_EQUIVALENT"
    DIVERGED_EXPECTEDLY = "DIVERGED_EXPECTEDLY"
    DIVERGED_UNEXPECTEDLY = "DIVERGED_UNEXPECTEDLY"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class ExperimentDefinitionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    definition_id: str = Field(..., description="Stable experiment definition slug")
    title: str
    description: str = ""


class ExperimentIDV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    definition: ExperimentDefinitionV1
    run_id: Id = Field(default_factory=new_id)


class ModelInvocationRecordV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    provider: str
    model_identifier: str
    model_version: Optional[str] = None
    endpoint_class: str = "serverless"
    request_schema_version: str = "1"
    structured_input_hash: str
    tool_schema_hash: Optional[str] = None
    response_hash: str
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latency_ms: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    prompt_disclosure: PromptDisclosure = PromptDisclosure.HASH_ONLY


class ToolInvocationRecordV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    tool_name: str
    tool_version: str
    container_digest: Optional[str] = None
    binary_hash: Optional[str] = None
    configuration_hash: Optional[str] = None


class InfrastructureRecordV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    region: str
    resource_class: str
    instance_template_id: Optional[str] = None
    image_or_snapshot_id: Optional[str] = None
    image_digest: Optional[str] = None
    vpc_config_hash: Optional[str] = None
    bootstrap_version: Optional[str] = None
    placement_plan_hash: Optional[str] = None


class ExperimentManifestV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    manifest_id: Id = Field(default_factory=new_id)
    experiment: ExperimentIDV1
    source_revision_id: Id
    source_hash: str
    twin_revision_id: Id
    twin_fingerprint: str
    range_spec_hash: str
    range_spec_version: str = "2"
    compiler_version: str
    compiler_policy_version: str = "sanitization/v1"
    fidelity_profile_id: Id
    fidelity_report_hash: Optional[str] = None
    investigation_objective: str
    remediation_candidates: list[str] = Field(default_factory=list)
    selected_remediation_id: Optional[Id] = None
    attack_replay_plan_id: Optional[Id] = None
    attack_replay_hash: Optional[str] = None
    verification_suite_id: Optional[Id] = None
    verification_suite_hash: Optional[str] = None
    scheduler_policy: str = "GHOSTSCHEDULER_V3"
    scheduler_policy_version: str = "ghostscheduler/v3"
    scheduler_config_hash: Optional[str] = None
    model_invocations: list[ModelInvocationRecordV1] = Field(default_factory=list)
    tool_invocations: list[ToolInvocationRecordV1] = Field(default_factory=list)
    infrastructure: Optional[InfrastructureRecordV1] = None
    budget_max_usd: Optional[float] = None
    started_at: AwareDatetime = Field(default_factory=utc_now)
    initiator: str = Field(..., description="Actor ref — not a secret")
    authorization_context_ref: Optional[str] = None


class ProvenanceNodeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    kind: ProvenanceNodeKind
    ref_id: str
    digest: Optional[str] = None
    label: str = ""


class ProvenanceEdgeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    from_node_id: Id
    to_node_id: Id
    kind: ProvenanceEdgeKind


class ProvenanceGraphV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    experiment_run_id: Id
    nodes: list[ProvenanceNodeV1] = Field(default_factory=list)
    edges: list[ProvenanceEdgeV1] = Field(default_factory=list)
    graph_digest: Optional[str] = None


class DisclosurePolicyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    level: DisclosureLevel = DisclosureLevel.INTERNAL
    redact_paths: list[str] = Field(default_factory=list)
    allow_hostname: bool = False


class ExperimentRootV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    manifest_digest: str
    provenance_graph_digest: str
    artifact_merkle_root: str
    event_log_root: str
    claim_set_digest: str
    root_digest: str


class GhostRangeExperimentPredicateV1(VersionedModel):
    """in-toto-compatible predicate body (typed, not envelope)."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    predicate_type: str = "https://ghostrange.local/attestation/experiment/v1"
    experiment_root: ExperimentRootV1
    manifest_id: Id
    replay_level_available: ReplayLevel = ReplayLevel.LEVEL_4


class ExperimentAttestationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    envelope_type: str = "application/vnd.in-toto+json"
    payload_type: str = "application/vnd.ghostrange.experimentpredicate+json"
    subject_digest: str = Field(..., description="sha256 digest of experiment root")
    predicate: GhostRangeExperimentPredicateV1
    signature_b64: str
    key_id: str
    signer_kind: SigningIdentityKind = SigningIdentityKind.LOCAL_DEVELOPMENT
    signed_at: AwareDatetime = Field(default_factory=utc_now)


class ArtifactIndexEntryV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    logical_name: str
    digest: str = Field(..., description="sha256:...")
    size_bytes: int = Field(..., ge=0)
    media_type: str = "application/octet-stream"


class GhostBundleV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    bundle_id: Id = Field(default_factory=new_id)
    mode: BundleMode
    manifest: ExperimentManifestV1
    provenance_graph: ProvenanceGraphV1
    experiment_root: ExperimentRootV1
    attestation: ExperimentAttestationV1
    artifact_index: list[ArtifactIndexEntryV1] = Field(default_factory=list)
    event_log: list[dict] = Field(default_factory=list)
    claims_digest: str
    replay_level: ReplayLevel = ReplayLevel.LEVEL_4
    disclosure: DisclosurePolicyV1 = Field(default_factory=DisclosurePolicyV1)
    bundle_digest: Optional[str] = None


class BundleVerificationResultV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    verified_integrity: bool
    structure_valid: VerificationDimensionStatus = VerificationDimensionStatus.SKIP
    hashes_valid: VerificationDimensionStatus = VerificationDimensionStatus.SKIP
    signature_valid: VerificationDimensionStatus = VerificationDimensionStatus.SKIP
    identity_valid: VerificationDimensionStatus = VerificationDimensionStatus.SKIP
    event_chain_valid: VerificationDimensionStatus = VerificationDimensionStatus.SKIP
    artifacts_complete: VerificationDimensionStatus = VerificationDimensionStatus.SKIP
    claim_references_valid: VerificationDimensionStatus = VerificationDimensionStatus.SKIP
    replayable: VerificationDimensionStatus = VerificationDimensionStatus.SKIP
    redaction_valid: VerificationDimensionStatus = VerificationDimensionStatus.SKIP
    failures: list[str] = Field(default_factory=list)


class ReplayPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    source_bundle_digest: str
    target_level: ReplayLevel
    pinned_images: dict[str, str] = Field(default_factory=dict)
    scheduler_policy: str = "ORIGINAL_POLICY"
    model_mode: str = "USE_RECORDED"
    estimated_cost_usd: Optional[float] = None


class ReplayComparisonV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    original_run_id: Id
    replay_run_id: Id
    world_fingerprint: ReplayEquivalence = ReplayEquivalence.NOT_COMPARABLE
    verification_result: ReplayEquivalence = ReplayEquivalence.NOT_COMPARABLE
    claim_outcome: ReplayEquivalence = ReplayEquivalence.NOT_COMPARABLE
    notes: list[str] = Field(default_factory=list)


class EventCheckpointV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    sequence: int = Field(..., ge=0)
    latest_event_hash: str
    experiment_run_id: Id
    checkpoint_digest: str
    signed: bool = False


__all__ = [
    "ReplayLevel",
    "DisclosureLevel",
    "BundleMode",
    "ExperimentManifestV1",
    "ExperimentIDV1",
    "ProvenanceGraphV1",
    "ExperimentRootV1",
    "ExperimentAttestationV1",
    "GhostBundleV1",
    "BundleVerificationResultV1",
    "ReplayPlanV1",
    "ReplayComparisonV1",
]
