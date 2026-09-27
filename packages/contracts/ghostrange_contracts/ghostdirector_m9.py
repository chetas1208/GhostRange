"""M9 GhostDirector — active experiment design (separate from GhostScheduler)."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field, model_validator

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class BeliefLevel(str, Enum):
    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class UncertaintyCategory(str, Enum):
    EXPLOITABILITY = "EXPLOITABILITY"
    REMEDIATION_EFFECTIVENESS = "REMEDIATION_EFFECTIVENESS"
    REGRESSION_RISK = "REGRESSION_RISK"
    ASSUMPTION_VALIDITY = "ASSUMPTION_VALIDITY"
    ATTACK_PATH = "ATTACK_PATH"
    DEPENDENCY_BEHAVIOR = "DEPENDENCY_BEHAVIOR"
    IDENTITY_BEHAVIOR = "IDENTITY_BEHAVIOR"
    CONFIGURATION = "CONFIGURATION"
    FIDELITY = "FIDELITY"
    COUNTEREXAMPLE_EXISTENCE = "COUNTEREXAMPLE_EXISTENCE"
    MODEL_DISAGREEMENT = "MODEL_DISAGREEMENT"
    UNKNOWN = "UNKNOWN"


class InvestigationHypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    REFUTED = "REFUTED"
    UNRESOLVED = "UNRESOLVED"


class HypothesisEdgeKind(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DEPENDS_ON = "DEPENDS_ON"
    REFINES = "REFINES"
    COMPETES_WITH = "COMPETES_WITH"
    EXPLAINS = "EXPLAINS"
    REQUIRES = "REQUIRES"


class ExperimentOperatorKind(str, Enum):
    REPLAY_ATTACK = "REPLAY_ATTACK"
    APPLY_CONTROLLED_CONFIG_VARIATION = "APPLY_CONTROLLED_CONFIG_VARIATION"
    CHANGE_SYNTHETIC_IDENTITY_STATE = "CHANGE_SYNTHETIC_IDENTITY_STATE"
    CHANGE_STUB_RESPONSE = "CHANGE_STUB_RESPONSE"
    RESTART_RANGE_SERVICE = "RESTART_RANGE_SERVICE"
    APPLY_REMEDIATION = "APPLY_REMEDIATION"
    RUN_REGRESSION = "RUN_REGRESSION"
    RUN_COUNTEREXAMPLE_SEARCH = "RUN_COUNTEREXAMPLE_SEARCH"
    COMPARE_WORLDS = "COMPARE_WORLDS"
    COLLECT_OBSERVATION = "COLLECT_OBSERVATION"


class CandidateOrigin(str, Enum):
    RULE = "RULE"
    MODEL = "MODEL"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    HUMAN = "HUMAN"
    DRIFT = "DRIFT"
    VERIFICATION_GAP = "VERIFICATION_GAP"
    FIDELITY_GAP = "FIDELITY_GAP"


class DirectorPolicyId(str, Enum):
    FIXED_SCRIPT = "FIXED_SCRIPT"
    RANDOM_SAFE = "RANDOM_SAFE"
    ROUND_ROBIN_UNCERTAINTY = "ROUND_ROBIN_UNCERTAINTY"
    GREEDY_INFORMATION = "GREEDY_INFORMATION"
    GREEDY_DECISION_VALUE = "GREEDY_DECISION_VALUE"
    GHOSTDIRECTOR_V1 = "GHOSTDIRECTOR_V1"
    ORACLE_BENCHMARK = "ORACLE_BENCHMARK"


class DirectorReasonCode(str, Enum):
    HIGH_DECISION_VALUE = "HIGH_DECISION_VALUE"
    HIGH_INFORMATION_GAIN = "HIGH_INFORMATION_GAIN"
    HIGH_SECURITY_IMPORTANCE = "HIGH_SECURITY_IMPORTANCE"
    RESOLVES_CONFLICT = "RESOLVES_CONFLICT"
    DISCRIMINATES_HYPOTHESES = "DISCRIMINATES_HYPOTHESES"
    CHEAP_INFORMATION = "CHEAP_INFORMATION"
    REPRESENTATIVE_TEST = "REPRESENTATIVE_TEST"
    ROBUSTNESS_CHECK = "ROBUSTNESS_CHECK"
    LOW_VALUE = "LOW_VALUE"
    REDUNDANT_EXPERIMENT = "REDUNDANT_EXPERIMENT"
    DOMINATED_EXPERIMENT = "DOMINATED_EXPERIMENT"
    BUDGET_PRESSURE = "BUDGET_PRESSURE"
    UNSAFE_EXPERIMENT = "UNSAFE_EXPERIMENT"
    INSUFFICIENT_FIDELITY = "INSUFFICIENT_FIDELITY"
    DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"
    MODEL_ONLY_UNSUPPORTED = "MODEL_ONLY_UNSUPPORTED"


class DirectorStopReason(str, Enum):
    DECISION_SUFFICIENT = "DECISION_SUFFICIENT"
    MANDATORY_VERIFICATION_COMPLETE = "MANDATORY_VERIFICATION_COMPLETE"
    UNCERTAINTY_BELOW_POLICY_THRESHOLD = "UNCERTAINTY_BELOW_POLICY_THRESHOLD"
    NO_HIGH_VALUE_EXPERIMENTS = "NO_HIGH_VALUE_EXPERIMENTS"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    TIME_EXHAUSTED = "TIME_EXHAUSTED"
    COUNTEREXAMPLE_CONFIRMED = "COUNTEREXAMPLE_CONFIRMED"
    HUMAN_STOP = "HUMAN_STOP"


class CampaignState(str, Enum):
    INITIALIZING = "INITIALIZING"
    ASSESSING = "ASSESSING"
    GENERATING = "GENERATING"
    SELECTING = "SELECTING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    UPDATING = "UPDATING"
    REASSESSING = "REASSESSING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class WorldExperimentalState(str, Enum):
    CLEAN = "CLEAN"
    MODIFIED = "MODIFIED"
    CONTAMINATED = "CONTAMINATED"
    RESET_REQUIRED = "RESET_REQUIRED"


class UncertaintyItemV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    subject: str
    proposition: str
    category: UncertaintyCategory
    importance: BeliefLevel = BeliefLevel.MEDIUM
    current_belief: BeliefLevel = BeliefLevel.UNKNOWN
    confidence_basis: str = ""
    supporting_evidence_ids: list[Id] = Field(default_factory=list)
    contradicting_evidence_ids: list[Id] = Field(default_factory=list)
    decision_relevance: BeliefLevel = BeliefLevel.MEDIUM
    resolution_conditions: list[str] = Field(default_factory=list)


class InvestigationHypothesisV1(VersionedModel):
    """M9 investigation hypothesis — not the incident ``HypothesisV1`` in hypothesis.py."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    investigation_id: Id
    statement: str
    hypothesis_type: str = "ROOT_CAUSE"
    related_claim_ids: list[Id] = Field(default_factory=list)
    related_assumption_ids: list[Id] = Field(default_factory=list)
    supporting_evidence_ids: list[Id] = Field(default_factory=list)
    contradicting_evidence_ids: list[Id] = Field(default_factory=list)
    status: InvestigationHypothesisStatus = InvestigationHypothesisStatus.PROPOSED
    priority: BeliefLevel = BeliefLevel.MEDIUM
    origin: CandidateOrigin = CandidateOrigin.RULE
    created_at: AwareDatetime = Field(default_factory=utc_now)


class HypothesisGraphEdgeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    from_hypothesis_id: Id
    to_hypothesis_id: Id
    kind: HypothesisEdgeKind


class HypothesisGraphV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    investigation_id: Id
    hypotheses: list[InvestigationHypothesisV1] = Field(default_factory=list)
    edges: list[HypothesisGraphEdgeV1] = Field(default_factory=list)


class InvestigationKnowledgeStateV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    investigation_id: Id
    objective: str
    claim_ids: list[Id] = Field(default_factory=list)
    hypothesis_graph: HypothesisGraphV1
    uncertainties: list[UncertaintyItemV1] = Field(default_factory=list)
    known_facts: list[str] = Field(default_factory=list)
    uncertain_facts: list[str] = Field(default_factory=list)
    counterexample_ids: list[Id] = Field(default_factory=list)
    remaining_questions: list[str] = Field(default_factory=list)
    experiment_history_ids: list[Id] = Field(default_factory=list)
    knowledge_state_hash: Optional[str] = None


class ExperimentOperatorV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    kind: ExperimentOperatorKind
    parameters: dict[str, Any] = Field(default_factory=dict)
    target_asset_id: Optional[str] = None


class ExpectedOutcomeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    if_hypothesis_id: Id
    observation_key: str
    expected_value: Any


class ExperimentProposalV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    investigation_id: Id
    objective: str
    hypotheses_tested: list[Id] = Field(default_factory=list)
    uncertainties_targeted: list[Id] = Field(default_factory=list)
    required_world_state: WorldExperimentalState = WorldExperimentalState.CLEAN
    operators: list[ExperimentOperatorV1] = Field(..., min_length=1)
    expected_outcomes: list[ExpectedOutcomeV1] = Field(default_factory=list)
    discriminating_power: BeliefLevel = BeliefLevel.MEDIUM
    estimated_cost_usd: float = Field(..., ge=0)
    estimated_runtime_sec: float = Field(..., ge=0)
    risk: BeliefLevel = BeliefLevel.LOW
    parallelizable: bool = True
    depends_on_experiment_ids: list[Id] = Field(default_factory=list)
    required_fidelity: str = "standard"
    origin: CandidateOrigin = CandidateOrigin.RULE
    fingerprint: str = ""


class ExperimentObservationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    experiment_id: Id
    world_id: Id
    operator_kind: ExperimentOperatorKind
    observable: str
    result: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[Id] = Field(default_factory=list)
    reliability: BeliefLevel = BeliefLevel.MEDIUM
    observed_at: AwareDatetime = Field(default_factory=utc_now)


class ExperimentUtilityV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    proposal_id: Id
    information_gain: float = Field(0, ge=0, le=1)
    decision_relevance: float = Field(0, ge=0, le=1)
    hypothesis_discrimination: float = Field(0, ge=0, le=1)
    expected_security_value: float = Field(0, ge=0, le=1)
    representativeness: float = Field(0, ge=0, le=1)
    robustness: float = Field(0, ge=0, le=1)
    compute_cost_usd: float = Field(0, ge=0)
    runtime_sec: float = Field(0, ge=0)
    experiment_risk: float = Field(0, ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class AcquisitionScoreV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    proposal_id: Id
    utility: ExperimentUtilityV1
    total_score: float
    policy_version: str = "ghostdirector/v1"
    components: dict[str, float] = Field(default_factory=dict)


class EvidenceConflictV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    investigation_id: Id
    observation_ids: list[Id] = Field(..., min_length=2)
    description: str
    resolution_priority: BeliefLevel = BeliefLevel.HIGH


class SurpriseObservationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    observation_id: Id
    unpredicted_by_hypothesis_ids: list[Id] = Field(default_factory=list)
    suggested_new_hypothesis: Optional[str] = None


class ExperimentCampaignBudgetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    max_experiments: int = Field(20, ge=1)
    max_worlds: int = Field(10, ge=1)
    max_compute_usd: float = Field(50.0, ge=0)
    max_model_usd: float = Field(10.0, ge=0)
    max_wall_time_sec: float = Field(3600, gt=0)
    reserved_usd: float = 0.0
    spent_usd: float = 0.0

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.max_compute_usd - self.spent_usd)


class ExperimentPortfolioV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    campaign_id: Id
    selected_proposal_ids: list[Id] = Field(default_factory=list)
    parallel_groups: list[list[Id]] = Field(default_factory=list)
    budget_allocation_usd: dict[str, float] = Field(default_factory=dict)
    expected_aggregate_value: float = 0.0


class DirectorDecisionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    knowledge_state_hash: str
    candidate_ids: list[Id] = Field(default_factory=list)
    selected_ids: list[Id] = Field(default_factory=list)
    rejected_ids: list[Id] = Field(default_factory=list)
    rejection_reasons: dict[str, DirectorReasonCode] = Field(default_factory=dict)
    utility_snapshots: list[AcquisitionScoreV1] = Field(default_factory=list)
    policy: DirectorPolicyId = DirectorPolicyId.GHOSTDIRECTOR_V1
    reason_codes: list[DirectorReasonCode] = Field(default_factory=list)
    decided_at: AwareDatetime = Field(default_factory=utc_now)


class ExperimentExecutionDAGV1(VersionedModel):
    """Handoff to GhostScheduler — WHAT becomes a task graph, not HOW to schedule it."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id
    nodes: list[Id] = Field(..., description="Experiment proposal ids")
    edges: list[tuple[Id, Id]] = Field(default_factory=list)
    parallel_groups: list[list[Id]] = Field(default_factory=list)


class ExperimentCampaignV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    investigation_id: Id
    policy: DirectorPolicyId
    budget: ExperimentCampaignBudgetV1 = Field(default_factory=ExperimentCampaignBudgetV1)
    state: CampaignState = CampaignState.INITIALIZING
    knowledge_state: InvestigationKnowledgeStateV1
    proposals: list[ExperimentProposalV1] = Field(default_factory=list)
    observations: list[ExperimentObservationV1] = Field(default_factory=list)
    decisions: list[DirectorDecisionV1] = Field(default_factory=list)
    stop_reason: Optional[DirectorStopReason] = None


class DirectorTraceV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    campaign_id: Id
    policy: DirectorPolicyId
    steps: list[dict[str, Any]] = Field(default_factory=list)


__all__ = [
    "BeliefLevel",
    "UncertaintyCategory",
    "InvestigationHypothesisStatus",
    "HypothesisEdgeKind",
    "ExperimentOperatorKind",
    "CandidateOrigin",
    "DirectorPolicyId",
    "DirectorReasonCode",
    "DirectorStopReason",
    "CampaignState",
    "WorldExperimentalState",
    "UncertaintyItemV1",
    "InvestigationHypothesisV1",
    "HypothesisGraphV1",
    "InvestigationKnowledgeStateV1",
    "ExperimentOperatorV1",
    "ExpectedOutcomeV1",
    "ExperimentProposalV1",
    "ExperimentObservationV1",
    "ExperimentUtilityV1",
    "AcquisitionScoreV1",
    "EvidenceConflictV1",
    "SurpriseObservationV1",
    "ExperimentCampaignBudgetV1",
    "ExperimentPortfolioV1",
    "DirectorDecisionV1",
    "ExperimentExecutionDAGV1",
    "ExperimentCampaignV1",
    "DirectorTraceV1",
]
