"""M6 Living Twin — revisions, drift, impact, claim validity, revalidation."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .fidelity_m5 import FidelityDimension, InvestigationObjectiveV1


class TwinRevisionStatus(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    RECOMPILING = "RECOMPILING"
    VALIDATING = "VALIDATING"
    SUPERSEDED = "SUPERSEDED"
    INVALID = "INVALID"


class DriftChangeType(str, Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"
    MODIFY = "MODIFY"
    MOVE = "MOVE"
    RENAME = "RENAME"
    UNKNOWN = "UNKNOWN"


class SemanticDriftCategory(str, Enum):
    TOPOLOGY = "TOPOLOGY"
    NETWORK = "NETWORK"
    SERVICE = "SERVICE"
    VERSION = "VERSION"
    CONFIGURATION = "CONFIGURATION"
    IDENTITY = "IDENTITY"
    DATA_SCHEMA = "DATA_SCHEMA"
    DATA_POLICY = "DATA_POLICY"
    RESOURCE = "RESOURCE"
    STORAGE = "STORAGE"
    DEPENDENCY = "DEPENDENCY"
    SECURITY_CONTROL = "SECURITY_CONTROL"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    UNKNOWN = "UNKNOWN"


class ImpactLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class ClaimValidityStatus(str, Enum):
    CURRENT = "CURRENT"
    POTENTIALLY_STALE = "POTENTIALLY_STALE"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"
    REVALIDATING = "REVALIDATING"
    SUPERSEDED = "SUPERSEDED"


class InvalidationReasonCode(str, Enum):
    SOURCE_PROPERTY_CHANGED = "SOURCE_PROPERTY_CHANGED"
    REQUIRED_FIDELITY_DRIFT = "REQUIRED_FIDELITY_DRIFT"
    BEHAVIORAL_INVARIANT_BROKEN = "BEHAVIORAL_INVARIANT_BROKEN"
    DEPENDENCY_CHANGED = "DEPENDENCY_CHANGED"
    VERIFICATION_SUITE_CHANGED = "VERIFICATION_SUITE_CHANGED"
    COMPILER_VERSION_CHANGED = "COMPILER_VERSION_CHANGED"
    UNKNOWN_IMPACT = "UNKNOWN_IMPACT"
    SOURCE_REVISION_SUPERSEDED = "SOURCE_REVISION_SUPERSEDED"
    FULL_REBUILD_REQUIRED = "FULL_REBUILD_REQUIRED"


class SyncDecision(str, Enum):
    IGNORE = "IGNORE"
    RECORD_ONLY = "RECORD_ONLY"
    INVALIDATE = "INVALIDATE"
    INCREMENTAL_SYNC = "INCREMENTAL_SYNC"
    FULL_SYNC = "FULL_SYNC"


class IncrementalAction(str, Enum):
    NOOP = "NOOP"
    UPDATE_CONFIG = "UPDATE_CONFIG"
    RESTART_SERVICE = "RESTART_SERVICE"
    REBUILD_CONTAINER = "REBUILD_CONTAINER"
    REPROVISION_COMPONENT = "REPROVISION_COMPONENT"
    REBUILD_NETWORK = "REBUILD_NETWORK"
    REBUILD_WORLD = "REBUILD_WORLD"


class SourceWatchMode(str, Enum):
    MANUAL = "MANUAL"
    ON_IMPORT = "ON_IMPORT"
    SCHEDULED = "SCHEDULED"


class SourceRevisionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    source_id: Id
    parent_revision_id: Optional[Id] = None
    timestamp: AwareDatetime = Field(default_factory=utc_now)
    source_hash: str
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    compiler_version: str = "range-compiler/v0.1"
    source_types: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class TwinRevisionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    twin_id: Id
    parent_twin_revision_id: Optional[Id] = None
    source_revision_id: Id
    blueprint_hash: str
    world_fingerprint: Optional[str] = None
    compiler_version: str
    fidelity_profile_id: Id
    status: TwinRevisionStatus = TwinRevisionStatus.CURRENT
    created_at: AwareDatetime = Field(default_factory=utc_now)


class DriftEventV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    source_revision_from: Id
    source_revision_to: Id
    stable_entity_id: str
    entity_name: str
    property_path: str
    change_type: DriftChangeType
    old_fingerprint: Optional[str] = None
    new_fingerprint: Optional[str] = None
    semantic_category: SemanticDriftCategory = SemanticDriftCategory.UNKNOWN
    detected_at: AwareDatetime = Field(default_factory=utc_now)
    confidence: float = Field(default=1.0, ge=0, le=1)
    provenance: str = ""


class DriftSetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    source_revision_from: Id
    source_revision_to: Id
    events: list[DriftEventV1] = Field(default_factory=list)
    formatting_only: bool = False
    created_at: AwareDatetime = Field(default_factory=utc_now)


class ImpactEdgeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    from_entity_id: str
    to_entity_id: str
    edge_kind: str
    propagated_categories: list[SemanticDriftCategory] = Field(default_factory=list)


class ImpactRecordV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    entity_id: str
    entity_name: str
    level: ImpactLevel
    categories: list[SemanticDriftCategory] = Field(default_factory=list)
    reason: str = ""


class ImpactGraphV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    drift_set_id: Id
    records: list[ImpactRecordV1] = Field(default_factory=list)
    edges: list[ImpactEdgeV1] = Field(default_factory=list)
    affected_claim_ids: list[Id] = Field(default_factory=list)


class ImpactRuleV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    drift_category: SemanticDriftCategory
    edge_kind: str
    resulting_level: ImpactLevel
    description: str = ""


class AssumptionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    claim_id: Id
    property_path: str
    expected_fingerprint: str
    description: str = ""


class ClaimDependencyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    claim_id: Id
    assumption_ids: list[Id] = Field(default_factory=list)
    invariant_ids: list[Id] = Field(default_factory=list)
    verification_ids: list[Id] = Field(default_factory=list)
    stable_entity_ids: list[str] = Field(default_factory=list)


class ClaimValidityV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    claim_id: Id
    status: ClaimValidityStatus = ClaimValidityStatus.CURRENT
    twin_revision_id: Id
    source_revision_id: Id
    reason_codes: list[InvalidationReasonCode] = Field(default_factory=list)
    explanation: Optional[str] = None
    updated_at: AwareDatetime = Field(default_factory=utc_now)


class EvidenceContextV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    evidence_id: Id
    source_revision_id: Id
    twin_revision_id: Id
    world_id: Id
    compiler_version: str
    verification_suite_version: str = "1"
    fidelity_profile_id: Id
    assumption_ids: list[Id] = Field(default_factory=list)


class TwinStalenessV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    twin_revision_id: Id
    topology_staleness: float = Field(default=0, ge=0, le=1)
    network_staleness: float = Field(default=0, ge=0, le=1)
    service_staleness: float = Field(default=0, ge=0, le=1)
    config_staleness: float = Field(default=0, ge=0, le=1)
    identity_staleness: float = Field(default=0, ge=0, le=1)
    resource_staleness: float = Field(default=0, ge=0, le=1)
    data_schema_staleness: float = Field(default=0, ge=0, le=1)
    overall_semantic: float = Field(default=0, ge=0, le=1)


class SyncPolicyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    watch_mode: SourceWatchMode = SourceWatchMode.ON_IMPORT
    unknown_impact_on_required_fidelity: SyncDecision = SyncDecision.INVALIDATE
    low_impact_decision: SyncDecision = SyncDecision.RECORD_ONLY
    high_impact_decision: SyncDecision = SyncDecision.INCREMENTAL_SYNC
    critical_impact_decision: SyncDecision = SyncDecision.FULL_SYNC


class IncrementalCompilationPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    twin_revision_from: Id
    twin_revision_to: Optional[Id] = None
    actions: list[IncrementalAction] = Field(default_factory=list)
    affected_entity_ids: list[str] = Field(default_factory=list)
    full_rebuild_required: bool = False
    reason: Optional[str] = None


class RevalidationPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    drift_set_id: Id
    impact_graph_id: Id
    affected_components: list[str] = Field(default_factory=list)
    fidelity_checks: list[str] = Field(default_factory=list)
    verification_tests: list[str] = Field(default_factory=list)
    claims_awaiting: list[Id] = Field(default_factory=list)
    unaffected_claim_ids: list[Id] = Field(default_factory=list)
    incremental_plan_id: Optional[Id] = None


class LivingTwinAnalysisV1(VersionedModel):
    """Bundle output of one drift→impact→sync decision pass."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    drift: DriftSetV1
    impact: ImpactGraphV1
    staleness: TwinStalenessV1
    sync_decision: SyncDecision
    revalidation: Optional[RevalidationPlanV1] = None
    incremental: Optional[IncrementalCompilationPlanV1] = None
    claim_updates: list[ClaimValidityV1] = Field(default_factory=list)


__all__ = [
    "TwinRevisionStatus",
    "DriftChangeType",
    "SemanticDriftCategory",
    "ImpactLevel",
    "ClaimValidityStatus",
    "InvalidationReasonCode",
    "SyncDecision",
    "IncrementalAction",
    "SourceWatchMode",
    "SourceRevisionV1",
    "TwinRevisionV1",
    "DriftEventV1",
    "DriftSetV1",
    "ImpactEdgeV1",
    "ImpactRecordV1",
    "ImpactGraphV1",
    "ImpactRuleV1",
    "AssumptionV1",
    "ClaimDependencyV1",
    "ClaimValidityV1",
    "EvidenceContextV1",
    "TwinStalenessV1",
    "SyncPolicyV1",
    "IncrementalCompilationPlanV1",
    "RevalidationPlanV1",
    "LivingTwinAnalysisV1",
]
