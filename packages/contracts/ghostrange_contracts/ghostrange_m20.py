"""M20 GhostRange One — unified campaign, release artifacts, event envelope."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class CampaignPhase(str, Enum):
    INGESTING = "INGESTING"
    TWIN_BUILDING = "TWIN_BUILDING"
    INVESTIGATING = "INVESTIGATING"
    EXPERIMENT_DESIGN = "EXPERIMENT_DESIGN"
    SCHEDULING = "SCHEDULING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    CAUSAL_ANALYSIS = "CAUSAL_ANALYSIS"
    REMEDIATION = "REMEDIATION"
    APPROVAL = "APPROVAL"
    OBSERVING = "OBSERVING"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class ReleaseMaturity(str, Enum):
    RESEARCH_PROTOTYPE = "RESEARCH_PROTOTYPE"
    CONTROLLED_DEPLOYMENT = "CONTROLLED_DEPLOYMENT"
    PILOT_READY = "PILOT_READY"
    PRODUCTION_CANDIDATE = "PRODUCTION_CANDIDATE"


class RealityClass(str, Enum):
    REAL_LIVE_VERIFIED = "REAL_LIVE_VERIFIED"
    REAL_CONTROLLED_LIVE = "REAL_CONTROLLED_LIVE"
    REAL_LOCAL_ONLY = "REAL_LOCAL_ONLY"
    SIMULATED = "SIMULATED"
    FIXTURE_ONLY = "FIXTURE_ONLY"
    MOCK_ONLY = "MOCK_ONLY"
    NOT_RUN = "NOT_RUN"
    NOT_INTEGRATED = "NOT_INTEGRATED"


class GhostCampaignV1(VersionedModel):
    """Single durable investigation identity — child entities reference campaign_id."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id = Field(default_factory=new_id)
    range_id: Id
    investigation_id: Id
    phase: CampaignPhase = CampaignPhase.INGESTING
    source_input_ref: str = ""
    twin_revision_id: Optional[Id] = None
    correlation_id: str = ""
    deploy_sha: str = "unknown"
    live_mode: str = "mock"
    created_at: AwareDatetime = Field(default_factory=utc_now)
    completed_at: Optional[AwareDatetime] = None


class CanonicalEventEnvelopeV1(VersionedModel):
    """Target shape for durable events (legacy rows may omit optional fields)."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    event_id: Id = Field(default_factory=new_id)
    event_type: str
    campaign_id: Id
    aggregate_type: str
    aggregate_id: Id
    aggregate_revision: int = 0
    timestamp: AwareDatetime = Field(default_factory=utc_now)
    source: str
    causation_id: Optional[Id] = None
    correlation_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class GhostCampaignReportV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    report_id: Id = Field(default_factory=new_id)
    campaign_id: Id
    range_id: Id
    incident_summary: str
    hypothesis_count: int = 0
    hypotheses_refuted: int = 0
    experiments_run: int = 0
    scheduler_decisions: int = 0
    counterexamples_confirmed: int = 0
    remediation_survivors: int = 0
    remediation_refuted: int = 0
    bundle_digest: Optional[str] = None
    arena_recommendation: Optional[str] = None
    cost_usd_estimate: float = 0.0
    limitations: list[str] = Field(default_factory=list)
    phases: list[str] = Field(default_factory=list)
    generated_at: AwareDatetime = Field(default_factory=utc_now)


class GhostEvidenceBundleV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    bundle_id: Id = Field(default_factory=new_id)
    campaign_id: Id
    manifest_digest: str = ""
    claims: list[dict[str, Any]] = Field(default_factory=list)
    event_summary_digest: str = ""
    scheduler_decision_count: int = 0
    verification_results: dict[str, Any] = Field(default_factory=dict)
    authorization_evidence: dict[str, Any] = Field(default_factory=dict)
    arena_qualification: Optional[str] = None
    checksums: dict[str, str] = Field(default_factory=dict)


class ReproductionManifestV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    manifest_id: Id = Field(default_factory=new_id)
    campaign_id: Id
    deploy_sha: str
    compose_path: str = ""
    director_policy: str = ""
    scheduler_policy: str = ""
    ghostshield_mode: str = ""
    inference_model: str = ""
    nondeterministic_components: list[str] = Field(default_factory=list)
    seed_notes: str = ""


__all__ = [
    "CampaignPhase",
    "CanonicalEventEnvelopeV1",
    "GhostCampaignReportV1",
    "GhostCampaignV1",
    "GhostEvidenceBundleV1",
    "RealityClass",
    "ReleaseMaturity",
    "ReproductionManifestV1",
]
