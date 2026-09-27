"""M8 Adversarial Verification — claim-bounded falsification contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field, model_validator

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class AdversarialClaimPhase(str, Enum):
    """UI-safe compact state — never 'SECURE'."""

    UNTESTED = "UNTESTED"
    SEARCHING = "SEARCHING"
    COUNTEREXAMPLE_FOUND = "COUNTEREXAMPLE_FOUND"
    SURVIVED_BUDGET = "SURVIVED_BUDGET"
    INCONCLUSIVE = "INCONCLUSIVE"
    PROVISIONALLY_VERIFIED = "PROVISIONALLY_VERIFIED"
    ADVERSARIAL_TESTING = "ADVERSARIAL_TESTING"
    HARDENED_VERIFIED = "HARDENED_VERIFIED"


class SearchPolicyId(str, Enum):
    UNIFORM_RANDOM = "UNIFORM_RANDOM"
    ROUND_ROBIN = "ROUND_ROBIN"
    STATIC_PRIORITY = "STATIC_PRIORITY"
    NOVELTY_GREEDY = "NOVELTY_GREEDY"
    GHOSTSCHEDULER_SEARCH = "GHOSTSCHEDULER_SEARCH"
    UCB = "UCB"


class SearchArmKind(str, Enum):
    HEADER_MUTATION = "HEADER_MUTATION"
    IDENTITY_STATE = "IDENTITY_STATE"
    SEQUENCE_MUTATION = "SEQUENCE_MUTATION"
    TIMING = "TIMING"
    PATH_VARIATION = "PATH_VARIATION"
    DEPENDENCY_VARIATION = "DEPENDENCY_VARIATION"
    PARAMETER_MUTATION = "PARAMETER_MUTATION"


class MutationKind(str, Enum):
    HEADER = "HEADER"
    PARAMETER = "PARAMETER"
    PATH = "PATH"
    BODY = "BODY"
    IDENTITY_STATE = "IDENTITY_STATE"
    REQUEST_SEQUENCE = "REQUEST_SEQUENCE"
    TIMING = "TIMING"
    DEPENDENCY_RESPONSE = "DEPENDENCY_RESPONSE"
    CONFIGURATION = "CONFIGURATION"


class CounterexampleReproducibility(str, Enum):
    UNCONFIRMED = "UNCONFIRMED"
    CONFIRMED = "CONFIRMED"
    REJECTED_FALSE_POSITIVE = "REJECTED_FALSE_POSITIVE"


class MinimalityLevel(str, Enum):
    NOT_MINIMIZED = "NOT_MINIMIZED"
    LOCALLY_MINIMIZED = "LOCALLY_MINIMIZED"


class SearchStopReason(str, Enum):
    COUNTEREXAMPLE_CONFIRMED = "COUNTEREXAMPLE_CONFIRMED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    COVERAGE_REACHED = "COVERAGE_REACHED"
    LOW_NOVELTY = "LOW_NOVELTY"
    STRATEGIES_EXHAUSTED = "STRATEGIES_EXHAUSTED"
    OPERATOR_STOP = "OPERATOR_STOP"


class OracleKind(str, Enum):
    HTTP_RESPONSE = "HTTP_RESPONSE"
    AUTHORIZATION_DECISION = "AUTHORIZATION_DECISION"
    SERVICE_LOG = "SERVICE_LOG"
    COMPOSITE = "COMPOSITE"


class FalsificationConditionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    claim_id: Id
    description: str
    machine_check: str = Field(
        ...,
        description="Stable predicate id, e.g. unauthenticated_admin_access",
    )
    required_observations: list[str] = Field(default_factory=list)


class AdversarialBudgetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    max_wall_time_sec: float = Field(300, gt=0)
    max_compute_cost_usd: float = Field(25.0, ge=0)
    max_model_cost_usd: float = Field(5.0, ge=0)
    max_worlds: int = Field(8, ge=1)
    max_attempts: int = Field(500, ge=1)
    max_parallel_searches: int = Field(4, ge=1)
    max_mutation_depth: int = Field(6, ge=1)
    max_sequence_length: int = Field(8, ge=1)
    max_remediation_revisions: int = Field(5, ge=0)
    confirmation_runs: int = Field(2, ge=1)


class MutationOperatorV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    kind: MutationKind
    arm: SearchArmKind
    parameters: dict[str, Any] = Field(default_factory=dict)
    policy_ref: str = "search-policy/v1"


class SearchCandidateV1(VersionedModel):
    """Typed executable search step — LLM output must validate into this."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    fingerprint: str
    world_asset_id: str = Field(..., description="Authorized range asset ref, not arbitrary URL")
    arm: SearchArmKind
    operators: list[MutationOperatorV1] = Field(..., min_length=1)
    action_sequence: list[dict[str, Any]] = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityOracleV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    kind: OracleKind
    falsification_condition_id: Id
    rules: dict[str, Any] = Field(default_factory=dict)


class AdversarialSearchPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    claim_id: Id
    world_id: Id
    baseline_world_id: Optional[Id] = None
    falsification_condition: FalsificationConditionV1
    search_objective: str
    authorized_asset_ids: list[str] = Field(..., min_length=1)
    entry_points: list[str] = Field(default_factory=list)
    enabled_arms: list[SearchArmKind] = Field(default_factory=list)
    budget: AdversarialBudgetV1 = Field(default_factory=AdversarialBudgetV1)
    search_policy: SearchPolicyId = SearchPolicyId.GHOSTSCHEDULER_SEARCH
    stop_conditions: list[SearchStopReason] = Field(default_factory=list)
    oracle: SecurityOracleV1


class ObservationNoveltyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    score: float = Field(..., ge=0, le=1)
    signals: list[str] = Field(default_factory=list)
    is_novel: bool = False


class SearchMemoryEntryV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    candidate_fingerprint: str
    arm: SearchArmKind
    result: str
    observation_digest: str
    cost_usd: float = 0.0
    novelty: ObservationNoveltyV1 = Field(default_factory=lambda: ObservationNoveltyV1(score=0.0))


class SearchMemoryV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    search_run_id: Id
    entries: list[SearchMemoryEntryV1] = Field(default_factory=list)


class SearchArmV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    kind: SearchArmKind
    attempts: int = 0
    successes: int = 0
    novel_observations: int = 0
    counterexamples: int = 0
    cost_usd: float = 0.0
    runtime_ms: float = 0.0
    priority_weight: float = 1.0


class SearchTreeNodeKind(str, Enum):
    HYPOTHESIS = "HYPOTHESIS"
    MUTATION = "MUTATION"
    EXECUTION = "EXECUTION"
    OBSERVATION = "OBSERVATION"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"


class SearchTreeEdgeKind(str, Enum):
    EXPANDS = "EXPANDS"
    MUTATES = "MUTATES"
    EXECUTES = "EXECUTES"
    OBSERVES = "OBSERVES"
    FALSIFIES = "FALSIFIES"


class SearchTreeNodeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    kind: SearchTreeNodeKind
    label: str = ""
    ref_id: Optional[str] = None


class SearchTreeEdgeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    from_node_id: Id
    to_node_id: Id
    kind: SearchTreeEdgeKind


class SearchTreeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    search_run_id: Id
    nodes: list[SearchTreeNodeV1] = Field(default_factory=list)
    edges: list[SearchTreeEdgeV1] = Field(default_factory=list)


class CounterexampleV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    claim_id: Id
    world_id: Id
    search_run_id: Id
    preconditions: list[str] = Field(default_factory=list)
    action_sequence: list[dict[str, Any]] = Field(..., min_length=1)
    observations: dict[str, Any] = Field(default_factory=dict)
    violated_invariant: str
    claim_contradiction: str
    reproducibility: CounterexampleReproducibility = CounterexampleReproducibility.UNCONFIRMED
    minimality: MinimalityLevel = MinimalityLevel.NOT_MINIMIZED
    original_complexity: int = 0
    minimized_complexity: int = 0
    confidence: float = Field(0.5, ge=0, le=1)
    evidence_ids: list[Id] = Field(default_factory=list)
    artifact_ids: list[Id] = Field(default_factory=list)
    discovered_by: SearchArmKind
    search_strategy: SearchPolicyId
    search_budget_snapshot: AdversarialBudgetV1
    created_at: AwareDatetime = Field(default_factory=utc_now)


class DifferentialObservationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    candidate_fingerprint: str
    baseline_world_id: Id
    remediated_world_id: Id
    baseline_oracle_satisfied: bool
    remediated_oracle_satisfied: bool
    interpretation: str


class AssumptionChallengeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    assumption_id: Id
    challenge_strategy: str
    required_world_state: dict[str, Any] = Field(default_factory=dict)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    expected_violation_condition: str
    result: str = "PENDING"


class RemediationRevisionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    parent_remediation_id: Id
    child_label: str = Field(..., description="e.g. Fix B.1")
    triggered_by_counterexample_id: Id
    change_summary: str


class VerificationTestSource(str, Enum):
    KNOWN = "KNOWN"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    MANUAL = "MANUAL"
    RESEARCH = "RESEARCH"


class VerificationSuiteRevisionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    suite_id: Id
    added_from: VerificationTestSource
    counterexample_id: Optional[Id] = None
    test_fingerprint: str


class AdversarialVerificationReportV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    claim_id: Id
    search_run_id: Id
    phase: AdversarialClaimPhase
    budget: AdversarialBudgetV1
    search_policy: SearchPolicyId
    attempts: int = 0
    worlds_used: int = 0
    coverage_summary: dict[str, float] = Field(default_factory=dict)
    counterexamples: list[CounterexampleV1] = Field(default_factory=list)
    unconfirmed_findings: int = 0
    cost_usd: float = 0.0
    runtime_sec: float = 0.0
    stop_reason: SearchStopReason
    limitations: list[str] = Field(default_factory=list)
    summary_statement: str = ""

    @model_validator(mode="after")
    def _honest_summary(self) -> "AdversarialVerificationReportV1":
        if not self.summary_statement and not self.counterexamples:
            if self.stop_reason in (
                SearchStopReason.BUDGET_EXHAUSTED,
                SearchStopReason.STRATEGIES_EXHAUSTED,
                SearchStopReason.LOW_NOVELTY,
            ):
                self.summary_statement = (
                    f"NO CONFIRMED COUNTEREXAMPLE FOUND WITHIN SEARCH BUDGET "
                    f"({self.attempts} attempts, policy={self.search_policy.value})."
                )
        return self


class CounterexampleBundleV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    counterexample: CounterexampleV1
    claim_statement: str
    assumption_ids: list[Id] = Field(default_factory=list)
    world_fingerprint: str = ""
    oracle: SecurityOracleV1
    ghostledger_bundle_ref: Optional[str] = None


__all__ = [
    "AdversarialClaimPhase",
    "SearchPolicyId",
    "SearchArmKind",
    "MutationKind",
    "FalsificationConditionV1",
    "AdversarialBudgetV1",
    "MutationOperatorV1",
    "SearchCandidateV1",
    "SecurityOracleV1",
    "AdversarialSearchPlanV1",
    "ObservationNoveltyV1",
    "SearchMemoryV1",
    "SearchArmV1",
    "SearchTreeV1",
    "CounterexampleV1",
    "DifferentialObservationV1",
    "AssumptionChallengeV1",
    "RemediationRevisionV1",
    "VerificationSuiteRevisionV1",
    "AdversarialVerificationReportV1",
    "CounterexampleBundleV1",
]
