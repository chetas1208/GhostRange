"""M18 GhostEvolve — verified experience to versioned candidate improvements."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class ExperienceClass(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    NEAR_MISS = "NEAR_MISS"
    RECOVERY = "RECOVERY"
    NEGATIVE_TRANSFER = "NEGATIVE_TRANSFER"
    SCHEDULING_MISPREDICTION = "SCHEDULING_MISPREDICTION"
    COST_OVERRUN = "COST_OVERRUN"
    STRAGGLER = "STRAGGLER"
    SPECULATION_WIN = "SPECULATION_WIN"
    SPECULATION_WASTE = "SPECULATION_WASTE"
    EARLY_STOP_SUCCESS = "EARLY_STOP_SUCCESS"
    EARLY_STOP_REGRET = "EARLY_STOP_REGRET"
    CAUSAL_DISCOVERY = "CAUSAL_DISCOVERY"
    COUNTEREXAMPLE_DISCOVERY = "COUNTEREXAMPLE_DISCOVERY"
    AUTHORIZATION_DENIAL = "AUTHORIZATION_DENIAL"


class LearningEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    ELIGIBLE_WITH_LIMITATIONS = "ELIGIBLE_WITH_LIMITATIONS"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class LearningSurface(str, Enum):
    SCHEDULER_RUNTIME_ESTIMATOR = "SCHEDULER_RUNTIME_ESTIMATOR"
    SCHEDULER_STARTUP_ESTIMATOR = "SCHEDULER_STARTUP_ESTIMATOR"
    SCHEDULER_COST_MODEL = "SCHEDULER_COST_MODEL"
    CPU_GPU_CROSSOVER = "CPU_GPU_CROSSOVER"
    STRAGGLER_MODEL = "STRAGGLER_MODEL"
    SPECULATION_POLICY = "SPECULATION_POLICY"
    WARM_RETENTION_POLICY = "WARM_RETENTION_POLICY"
    TASK_PRIORITY_POLICY = "TASK_PRIORITY_POLICY"
    DIRECTOR_EXPERIMENT_RANKING = "DIRECTOR_EXPERIMENT_RANKING"
    COUNTEREXAMPLE_SEARCH_PRIOR = "COUNTEREXAMPLE_SEARCH_PRIOR"
    STOPPING_POLICY = "STOPPING_POLICY"
    RETRIEVAL_RANKING = "RETRIEVAL_RANKING"
    MEMORY_SELECTION = "MEMORY_SELECTION"


class EvolutionCandidateState(str, Enum):
    PROPOSED = "PROPOSED"
    TRAINING = "TRAINING"
    TRAINED = "TRAINED"
    OFFLINE_EVALUATION = "OFFLINE_EVALUATION"
    REJECTED = "REJECTED"
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"
    SUPERSEDED = "SUPERSEDED"


class PromotionLevel(str, Enum):
    OFFLINE_ONLY = "OFFLINE_ONLY"
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    PRODUCTION = "PRODUCTION"


class DriftKind(str, Enum):
    INPUT_DRIFT = "INPUT_DRIFT"
    WORKLOAD_DRIFT = "WORKLOAD_DRIFT"
    RUNTIME_DRIFT = "RUNTIME_DRIFT"
    PROVIDER_DRIFT = "PROVIDER_DRIFT"
    COST_DRIFT = "COST_DRIFT"
    POLICY_DRIFT = "POLICY_DRIFT"
    MODEL_DRIFT = "MODEL_DRIFT"
    RETRIEVAL_DRIFT = "RETRIEVAL_DRIFT"


class ExperienceRecordV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    experience_id: Id = Field(default_factory=new_id)
    campaign_id: Id
    task_id: Optional[Id] = None
    experiment_id: Optional[Id] = None
    system_revision: str = ""
    policy_revision: str = ""
    scheduler_revision: str = ""
    experience_class: ExperienceClass = ExperienceClass.SUCCESS
    context: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    predictions: dict[str, Any] = Field(default_factory=dict)
    actual_outcome: dict[str, Any] = Field(default_factory=dict)
    cost_usd: float = Field(default=0.0, ge=0)
    latency_seconds: float = Field(default=0.0, ge=0)
    evidence_yield: float = Field(default=0.0, ge=0)
    failures: list[str] = Field(default_factory=list)
    recovery: dict[str, Any] = Field(default_factory=dict)
    safety_outcome: str = "OK"
    provenance_digest: str = ""
    learning_eligibility: LearningEligibility = LearningEligibility.INSUFFICIENT_EVIDENCE
    recorded_at: AwareDatetime = Field(default_factory=utc_now)
    immutable_raw_digest: str = ""

    def compute_immutable_digest(self) -> str:
        payload = {
            "campaign_id": str(self.campaign_id),
            "task_id": str(self.task_id) if self.task_id else None,
            "context": self.context,
            "actual_outcome": self.actual_outcome,
            "recorded_at": self.recorded_at.isoformat(),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


class LearningEligibilityV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    experience_id: Id
    eligibility: LearningEligibility
    reason_codes: list[str] = Field(default_factory=list)
    evaluated_at: AwareDatetime = Field(default_factory=utc_now)


class ExperienceApplicabilityV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    experience_id: Id
    target_surface: LearningSurface
    score: float = Field(..., ge=0, le=1)
    mechanism_similarity: float = Field(default=0.0, ge=0, le=1)
    recency_weight: float = Field(default=1.0, ge=0)


class ImprovementOpportunityV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    opportunity_id: Id = Field(default_factory=new_id)
    learning_surface: LearningSurface
    summary: str
    supporting_experience_ids: list[Id] = Field(default_factory=list)
    confidence: str = "STATISTICAL"  # SINGLE_CASE_HYPOTHESIS | STATISTICAL
    created_at: AwareDatetime = Field(default_factory=utc_now)


class CapabilitySelfAssessmentV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    surface: LearningSurface
    slice_key: str
    metric_name: str
    observed_value: float
    baseline_value: float
    sample_count: int = Field(..., ge=0)
    assessed_at: AwareDatetime = Field(default_factory=utc_now)


class ImprovementAttributionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    attribution_id: Id = Field(default_factory=new_id)
    bottleneck_surface: LearningSurface
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)


class ImprovementProposalV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    proposal_id: Id = Field(default_factory=new_id)
    learning_surface: LearningSurface
    baseline_version: str
    candidate_version: str
    motivation: str
    supporting_experience_ids: list[Id] = Field(default_factory=list)
    training_data_revision: str
    proposed_change: dict[str, Any] = Field(default_factory=dict)
    expected_benefit: str = ""
    known_risks: list[str] = Field(default_factory=list)
    evaluation_plan: list[str] = Field(default_factory=list)
    rollback_plan: str = ""


class EvolutionCandidateV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    candidate_id: Id = Field(default_factory=new_id)
    learning_surface: LearningSurface
    version_label: str
    state: EvolutionCandidateState = EvolutionCandidateState.PROPOSED
    champion_version: str
    artifact_digest: str = ""
    training_manifest_digest: str = ""
    policy_that_generated_experience: str = ""
    created_at: AwareDatetime = Field(default_factory=utc_now)

    def candidate_digest(self) -> str:
        payload = {
            "learning_surface": self.learning_surface.value,
            "version_label": self.version_label,
            "artifact_digest": self.artifact_digest,
            "training_manifest_digest": self.training_manifest_digest,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


class ForgettingReportV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    candidate_version: str
    champion_version: str
    old_workload_metric_delta: float
    acceptable_regression_budget: float
    passed: bool
    slices: dict[str, float] = Field(default_factory=dict)


class DriftSignalV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    drift_id: Id = Field(default_factory=new_id)
    kind: DriftKind
    surface: LearningSurface
    detail: str
    trigger_evaluation_only: bool = True
    detected_at: AwareDatetime = Field(default_factory=utc_now)


class EvolutionPromotionRequestV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    request_id: Id = Field(default_factory=new_id)
    candidate_digest: str
    baseline_digest: str
    evaluation_digest: str
    regression_passed: bool
    safety_passed: bool
    shadow_passed: bool
    canary_plan: str = ""
    rollback_target_version: str
    human_approval_digest: Optional[str] = None
    promotion_level: PromotionLevel = PromotionLevel.PRODUCTION
    arena_release_report_digest: Optional[str] = None
    arena_qualified: bool = False

    def request_digest(self) -> str:
        raw = json.dumps(
            {
                "candidate_digest": self.candidate_digest,
                "evaluation_digest": self.evaluation_digest,
                "rollback_target_version": self.rollback_target_version,
            },
            sort_keys=True,
        ).encode()
        return hashlib.sha256(raw).hexdigest()


class EvolutionRollbackV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    rollback_id: Id = Field(default_factory=new_id)
    from_version: str
    to_version: str
    reason: str
    preauthorized: bool = True
    rolled_back_at: AwareDatetime = Field(default_factory=utc_now)


class EvolutionBudgetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    max_training_usd: float = Field(default=50.0, ge=0)
    max_evaluation_usd: float = Field(default=25.0, ge=0)
    max_shadow_decisions: int = Field(default=10_000, ge=0)
    max_canary_fraction: float = Field(default=0.05, ge=0, le=1)


class EvolutionValueReportV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    candidate_version: str
    training_cost_usd: float
    evaluation_cost_usd: float
    expected_savings_per_run_usd: float
    amortization_runs_to_breakeven: Optional[float] = None
    worthwhile: bool = False


FORBIDDEN_LEARNING_SURFACES: frozenset[LearningSurface] = frozenset()

__all__ = [
    "CapabilitySelfAssessmentV1",
    "DriftKind",
    "DriftSignalV1",
    "EvolutionBudgetV1",
    "EvolutionCandidateState",
    "EvolutionCandidateV1",
    "EvolutionPromotionRequestV1",
    "EvolutionRollbackV1",
    "EvolutionValueReportV1",
    "ExperienceApplicabilityV1",
    "ExperienceClass",
    "ExperienceRecordV1",
    "FORBIDDEN_LEARNING_SURFACES",
    "ForgettingReportV1",
    "ImprovementAttributionV1",
    "ImprovementOpportunityV1",
    "ImprovementProposalV1",
    "LearningEligibility",
    "LearningEligibilityV1",
    "LearningSurface",
    "PromotionLevel",
]
