"""M19 GhostArena — independent evaluation contracts (learner must not see hidden bundles)."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class ScenarioFamily(str, Enum):
    INCIDENT_TRIAGE = "INCIDENT_TRIAGE"
    REMEDIATION_DISCOVERY = "REMEDIATION_DISCOVERY"
    COUNTEREXAMPLE_SEARCH = "COUNTEREXAMPLE_SEARCH"
    CAUSAL_DISCRIMINATION = "CAUSAL_DISCRIMINATION"
    COMPUTE_SCHEDULING = "COMPUTE_SCHEDULING"
    FAILURE_RECOVERY = "FAILURE_RECOVERY"
    AUTHORIZATION_SAFETY = "AUTHORIZATION_SAFETY"
    MESH_TRANSFER = "MESH_TRANSFER"
    GHOSTWATCH_OBSERVATION = "GHOSTWATCH_OBSERVATION"
    SELF_IMPROVEMENT_EVALUATION = "SELF_IMPROVEMENT_EVALUATION"


class SuiteType(str, Enum):
    REGRESSION = "REGRESSION"
    GENERALIZATION = "GENERALIZATION"
    ADVERSARIAL = "ADVERSARIAL"
    SAFETY = "SAFETY"
    RELIABILITY = "RELIABILITY"
    COST = "COST"
    DRIFT = "DRIFT"
    FRONTIER = "FRONTIER"


class HorizonClass(str, Enum):
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    LONG = "LONG"
    VERY_LONG = "VERY_LONG"


class ArenaFailureType(str, Enum):
    PLANNING_ERROR = "PLANNING_ERROR"
    PREMATURE_STOP = "PREMATURE_STOP"
    REWARD_HACK = "REWARD_HACK"
    FABRICATED_SUCCESS = "FABRICATED_SUCCESS"
    SAFETY_VIOLATION = "SAFETY_VIOLATION"
    MISSED_COUNTEREXAMPLE = "MISSED_COUNTEREXAMPLE"
    BUDGET_OVERRUN = "BUDGET_OVERRUN"
    OVERCOMPUTE = "OVERCOMPUTE"
    RECOVERY_FAILURE = "RECOVERY_FAILURE"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"


class RunQualification(str, Enum):
    SUCCESS_CLEAN = "SUCCESS_CLEAN"
    SUCCESS_WITH_RECOVERED_ERRORS = "SUCCESS_WITH_RECOVERED_ERRORS"
    SUCCESS_WITH_POLICY_VIOLATION = "SUCCESS_WITH_POLICY_VIOLATION"
    FAILURE = "FAILURE"
    INVALID_EVALUATION = "INVALID_EVALUATION"


class ReleaseRecommendation(str, Enum):
    QUALIFIED = "QUALIFIED"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class BenchmarkLifecycle(str, Enum):
    PRIVATE = "PRIVATE"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    DISCLOSED = "DISCLOSED"


class ArenaHiddenBundleV1(VersionedModel):
    """Evaluator-only — must not ship in production runtime artifacts."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    bundle_id: Id = Field(default_factory=new_id)
    scenario_id: str
    seed: int
    ground_truth: dict[str, Any] = Field(default_factory=dict)
    hidden_verifier_spec: dict[str, Any] = Field(default_factory=dict)
    expected_invariants: list[str] = Field(default_factory=list)
    lifecycle: BenchmarkLifecycle = BenchmarkLifecycle.PRIVATE


class ArenaScenarioV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    scenario_id: str
    scenario_version: str = "1"
    scenario_family: ScenarioFamily
    suite_type: SuiteType = SuiteType.GENERALIZATION
    horizon: HorizonClass = HorizonClass.MEDIUM
    visible_instruction: str
    environment_revision: str = "arena-env/v1"
    time_budget_seconds: float = Field(default=300.0, ge=0)
    compute_budget_usd: float = Field(default=5.0, ge=0)
    hidden_bundle_reference: str = ""


class OutcomeVerifierV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    passed: bool
    details: str = ""


class ProcessVerifierV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    passed: bool
    violations: list[str] = Field(default_factory=list)


class SafetyVerifierV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    passed: bool
    violations: list[str] = Field(default_factory=list)


class TrajectoryVerifierV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    passed: bool
    step_count: int = 0


class FailureLocalizationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    first_failure_step: int
    failure_type: ArenaFailureType
    expected_behavior: str
    observed_behavior: str
    downstream_effects: list[str] = Field(default_factory=list)


class CapabilityProfileV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    investigation_correctness: float = 0.0
    counterexample_discovery: float = 0.0
    scheduler_efficiency: float = 0.0
    authorization_safety: float = 1.0
    recovery: float = 0.0
    cost_efficiency: float = 0.0


class GhostArenaReleaseReportV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    report_id: Id = Field(default_factory=new_id)
    baseline_version: str
    candidate_version: str
    suite_types: list[SuiteType] = Field(default_factory=list)
    scenario_count: int = 0
    seeds_per_scenario: int = 1
    recommendation: ReleaseRecommendation
    capability_delta: dict[str, float] = Field(default_factory=dict)
    safety_regression: bool = False
    hidden_generalization_regression: bool = False
    cost_delta_pct: Optional[float] = None
    sanitized_diagnostics: list[str] = Field(default_factory=list)
    failures: list[ArenaFailureType] = Field(default_factory=list)
    issued_at: AwareDatetime = Field(default_factory=utc_now)

    def qualifies_promotion(self) -> bool:
        return self.recommendation == ReleaseRecommendation.QUALIFIED and not self.safety_regression


class ArenaRunRecordV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    run_id: Id = Field(default_factory=new_id)
    scenario_id: str
    baseline_version: str
    candidate_version: str
    seed: int
    outcome: OutcomeVerifierV1
    process: ProcessVerifierV1
    safety: SafetyVerifierV1
    qualification: RunQualification
    failure_localization: Optional[FailureLocalizationV1] = None
    trajectory_digest_sha256: str = ""


__all__ = [
    "ArenaFailureType",
    "ArenaHiddenBundleV1",
    "ArenaRunRecordV1",
    "ArenaScenarioV1",
    "BenchmarkLifecycle",
    "CapabilityProfileV1",
    "FailureLocalizationV1",
    "GhostArenaReleaseReportV1",
    "HorizonClass",
    "OutcomeVerifierV1",
    "ProcessVerifierV1",
    "ReleaseRecommendation",
    "RunQualification",
    "SafetyVerifierV1",
    "ScenarioFamily",
    "SuiteType",
    "TrajectoryVerifierV1",
]
