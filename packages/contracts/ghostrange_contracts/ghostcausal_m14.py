"""M14 GhostCausal — mechanism discovery, interventions, transportability."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class CausalAssumptionKind(str, Enum):
    NO_UNMEASURED_CONFOUNDING = "NO_UNMEASURED_CONFOUNDING"
    CAUSAL_SUFFICIENCY = "CAUSAL_SUFFICIENCY"
    MECHANISM_INVARIANCE = "MECHANISM_INVARIANCE"
    POSITIVITY = "POSITIVITY"
    CONSISTENCY = "CONSISTENCY"
    SUTVA_LIKE = "SUTVA_LIKE"
    TEMPORAL_ORDER = "TEMPORAL_ORDER"
    NO_INTERFERENCE = "NO_INTERFERENCE"
    MEASUREMENT_RELIABILITY = "MEASUREMENT_RELIABILITY"
    SELECTION_MODEL = "SELECTION_MODEL"
    LATENT_VARIABLE_ALLOWED = "LATENT_VARIABLE_ALLOWED"
    DOMAIN_SHIFT_ASSUMPTION = "DOMAIN_SHIFT_ASSUMPTION"


class CausalValidityStatus(str, Enum):
    OBSERVATIONAL_ONLY = "OBSERVATIONAL_ONLY"
    ASSUMPTION_DEPENDENT = "ASSUMPTION_DEPENDENT"
    INTERVENTION_SUPPORTED = "INTERVENTION_SUPPORTED"
    COUNTERFACTUALLY_SUPPORTED = "COUNTERFACTUALLY_SUPPORTED"
    TRANSPORTABLE_UNDER_ASSUMPTIONS = "TRANSPORTABLE_UNDER_ASSUMPTIONS"
    NOT_IDENTIFIABLE = "NOT_IDENTIFIABLE"
    CONTRADICTED = "CONTRADICTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class CausalVariableCategory(str, Enum):
    CONFIGURATION = "CONFIGURATION"
    IDENTITY_STATE = "IDENTITY_STATE"
    SESSION_STATE = "SESSION_STATE"
    SERVICE_STATE = "SERVICE_STATE"
    DEPENDENCY_BEHAVIOR = "DEPENDENCY_BEHAVIOR"
    NETWORK_POLICY = "NETWORK_POLICY"
    REQUEST_ORDER = "REQUEST_ORDER"
    CACHE_STATE = "CACHE_STATE"
    DEPLOYMENT_REVISION = "DEPLOYMENT_REVISION"
    SECURITY_OUTCOME = "SECURITY_OUTCOME"
    HEALTH_OUTCOME = "HEALTH_OUTCOME"
    VERIFICATION_OUTCOME = "VERIFICATION_OUTCOME"


class CausalEdgeKind(str, Enum):
    CAUSES = "CAUSES"
    POSSIBLY_CAUSES = "POSSIBLY_CAUSES"
    CONFOUNDED_WITH = "CONFOUNDED_WITH"
    MEDIATES = "MEDIATES"
    MODIFIES_EFFECT = "MODIFIES_EFFECT"
    SELECTION_DEPENDS_ON = "SELECTION_DEPENDS_ON"


class CausalEdgeStatus(str, Enum):
    HYPOTHESIZED = "HYPOTHESIZED"
    OBSERVATION_SUPPORTED = "OBSERVATION_SUPPORTED"
    INTERVENTION_SUPPORTED = "INTERVENTION_SUPPORTED"
    REFUTED = "REFUTED"
    UNIDENTIFIED = "UNIDENTIFIED"


class CausalEdgeOrigin(str, Enum):
    TOPOLOGY_DERIVED = "TOPOLOGY_DERIVED"
    MODEL_PROPOSED = "MODEL_PROPOSED"
    MESH_PRIOR = "MESH_PRIOR"
    OBSERVATION_INFERRED = "OBSERVATION_INFERRED"
    INTERVENTION_SUPPORTED = "INTERVENTION_SUPPORTED"


class CausalClaimLifecycle(str, Enum):
    PROPOSED = "PROPOSED"
    OBSERVATIONAL = "OBSERVATIONAL"
    INTERVENTION_SUPPORTED = "INTERVENTION_SUPPORTED"
    COUNTERFACTUAL_SUPPORTED = "COUNTERFACTUAL_SUPPORTED"
    TRANSPORTABLE = "TRANSPORTABLE"
    STALE = "STALE"
    REFUTED = "REFUTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class CausalInvestigationState(str, Enum):
    INITIALIZING = "INITIALIZING"
    OBSERVATIONAL_ANALYSIS = "OBSERVATIONAL_ANALYSIS"
    MECHANISM_HYPOTHESES = "MECHANISM_HYPOTHESES"
    EXPERIMENT_DESIGN = "EXPERIMENT_DESIGN"
    INTERVENTION_RUNNING = "INTERVENTION_RUNNING"
    UPDATING_MODEL = "UPDATING_MODEL"
    COUNTERFACTUAL_ANALYSIS = "COUNTERFACTUAL_ANALYSIS"
    TRANSPORTABILITY_ANALYSIS = "TRANSPORTABILITY_ANALYSIS"
    CONCLUDED = "CONCLUDED"
    INCONCLUSIVE = "INCONCLUSIVE"
    FAILED = "FAILED"


class TransportabilityStatus(str, Enum):
    TRANSPORTABLE = "TRANSPORTABLE"
    PARTIALLY_TRANSPORTABLE = "PARTIALLY_TRANSPORTABLE"
    NOT_TRANSPORTABLE = "NOT_TRANSPORTABLE"
    NOT_IDENTIFIABLE = "NOT_IDENTIFIABLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class CausalAssumptionV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    assumption_id: str
    kind: CausalAssumptionKind
    established: bool = False
    notes: str = ""


class CausalVariableV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    variable_id: str
    name: str
    category: CausalVariableCategory
    observable: bool = True


class CausalEdgeV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    source_id: str
    target_id: str
    kind: CausalEdgeKind = CausalEdgeKind.POSSIBLY_CAUSES
    status: CausalEdgeStatus = CausalEdgeStatus.HYPOTHESIZED
    origin: CausalEdgeOrigin = CausalEdgeOrigin.OBSERVATION_INFERRED
    assumption_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class CausalGraphRevisionV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    revision_id: Id = Field(default_factory=new_id)
    parent_revision_id: Optional[Id] = None
    created_at: AwareDatetime = Field(default_factory=utc_now)
    edges: list[CausalEdgeV1] = Field(default_factory=list)
    variables: list[CausalVariableV1] = Field(default_factory=list)


class CausalGraphV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    graph_id: Id = Field(default_factory=new_id)
    investigation_id: Id = Field(default_factory=new_id)
    current_revision: CausalGraphRevisionV1 = Field(default_factory=CausalGraphRevisionV1)
    assumptions: list[CausalAssumptionV1] = Field(default_factory=list)


class CausalInterventionV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    intervention_id: Id = Field(default_factory=new_id)
    variable_id: str
    action: str
    scope: str = "DISPOSABLE_WORLD"
    world_label: str = ""
    preconditions: list[str] = Field(default_factory=list)
    expected_mechanism: str = ""
    safety_classification: str = "RANGE_BOUND"
    cost_usd_estimate: float = 0.5


class CausalClaimV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    claim_id: Id = Field(default_factory=new_id)
    statement: str
    lifecycle: CausalClaimLifecycle = CausalClaimLifecycle.PROPOSED
    validity: CausalValidityStatus = CausalValidityStatus.OBSERVATIONAL_ONLY
    assumption_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    linked_security_claim_id: Optional[Id] = None


class CausalDiscoveryMethodProfileV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    method: str
    data_type: str = "multivariate_observational"
    assumptions: list[CausalAssumptionKind] = Field(default_factory=list)
    supports_latent_confounding: bool = False
    supports_temporal_data: bool = False
    requires_interventions: bool = False
    failure_modes: list[str] = Field(default_factory=list)


class InvariantMechanismV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    cause_ids: list[str]
    effect_id: str
    domains_tested: list[str] = Field(default_factory=list)
    invariance_evidence: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    assumption_ids: list[str] = Field(default_factory=list)


class CausalFidelityProfileV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    mechanism_id: str
    identity_semantics: float = Field(ge=0.0, le=1.0, default=0.0)
    cache_behavior: float = Field(ge=0.0, le=1.0, default=0.0)
    network_ordering: float = Field(ge=0.0, le=1.0, default=0.0)
    overall_sufficient: bool = False


class CausalRootCauseReportV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    report_id: Id = Field(default_factory=new_id)
    outcome_variable_id: str
    supported_causes: list[str] = Field(default_factory=list)
    refuted_hypotheses: list[str] = Field(default_factory=list)
    remaining_confounders: list[str] = Field(default_factory=list)
    validity: CausalValidityStatus = CausalValidityStatus.INCONCLUSIVE


class SecurityCounterfactualV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    counterfactual_id: Id = Field(default_factory=new_id)
    query: str
    intervention_description: str
    predicted_outcome: str
    assumptions: list[str] = Field(default_factory=list)


class CounterfactualValidityV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    counterfactual_id: Id
    identifiable: bool = False
    model_support: CausalValidityStatus = CausalValidityStatus.ASSUMPTION_DEPENDENT
    experimental_corroboration: Optional[bool] = None
    uncertainty_notes: str = ""


class MinimalInterventionCandidateV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    variable_ids: list[str]
    description: str
    locally_minimal: bool = False
    evidence_refs: list[str] = Field(default_factory=list)


class DomainDifferenceGraphV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    source_domain: str
    target_domain: str
    shared_mechanisms: list[str] = Field(default_factory=list)
    differing_mechanisms: list[str] = Field(default_factory=list)


class TransportabilityQueryV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    query_id: Id = Field(default_factory=new_id)
    source_domain: str
    target_domain: str
    causal_query: str
    mechanism_path: list[str] = Field(default_factory=list)
    assumption_ids: list[str] = Field(default_factory=list)


class TransportabilityReportV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    query_id: Id
    status: TransportabilityStatus
    shared_mechanisms: list[str] = Field(default_factory=list)
    differing_mechanisms: list[str] = Field(default_factory=list)
    required_assumptions: list[str] = Field(default_factory=list)
    limitations: str = ""
    recommended_local_experiment: Optional[str] = None


class CausalMeshContributionV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    abstract_variables: list[str] = Field(default_factory=list)
    abstract_mechanism_path: list[str] = Field(default_factory=list)
    intervention_class: str = ""
    effect_class: str = ""
    assumption_profile: list[str] = Field(default_factory=list)
    provenance_digest: str = ""


class CausalContributionPrivacyV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    fields_generalized: list[str] = Field(default_factory=list)
    topology_leakage_risk: str = "UNEVALUATED"


class CausalExperimentProposalV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    proposal_id: Id = Field(default_factory=new_id)
    candidate_mechanisms: list[str] = Field(default_factory=list)
    interventions: list[CausalInterventionV1] = Field(default_factory=list)
    identification_objective: str = ""
    causal_discrimination_value: float = Field(ge=0.0, le=1.0, default=0.0)
    cost_usd_estimate: float = 0.0


class CausalInvestigationV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    investigation_id: Id = Field(default_factory=new_id)
    state: CausalInvestigationState = CausalInvestigationState.INITIALIZING
    graph: CausalGraphV1 = Field(default_factory=CausalGraphV1)
    claims: list[CausalClaimV1] = Field(default_factory=list)


class CausalHypothesisDraftV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    draft_id: Id = Field(default_factory=new_id)
    proposed_edges: list[CausalEdgeV1] = Field(default_factory=list)
    model_origin: bool = True
    validated: bool = False


class CausalSurpriseV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    expected_outcome: str
    observed_outcome: str
    intervention_id: Optional[Id] = None


class CausalDomainV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    domain_id: str
    world_id: Optional[str] = None
    twin_revision: str = ""
    configuration_fingerprint: str = ""


class CausalPathV1(VersionedModel):
    schema_version: Literal["1"] = "1"
    nodes: list[str]
    edge_kinds: list[CausalEdgeKind] = Field(default_factory=list)
