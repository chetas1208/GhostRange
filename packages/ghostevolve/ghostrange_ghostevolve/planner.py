"""EvolutionPlanner — what surface to improve, not auto-change."""

from __future__ import annotations

from ghostrange_contracts.ghostevolve_m18 import (
    CapabilitySelfAssessmentV1,
    ImprovementAttributionV1,
    ImprovementOpportunityV1,
    LearningSurface,
)


class EvolutionPlanner:
    def identify_bottleneck(
        self, assessments: list[CapabilitySelfAssessmentV1]
    ) -> ImprovementAttributionV1 | None:
        runtime = [a for a in assessments if a.surface == LearningSurface.SCHEDULER_RUNTIME_ESTIMATOR]
        placement = [a for a in assessments if a.surface == LearningSurface.TASK_PRIORITY_POLICY]
        if runtime:
            worst = max(runtime, key=lambda a: a.observed_value - a.baseline_value)
            if worst.observed_value > worst.baseline_value * 1.2:
                return ImprovementAttributionV1(
                    bottleneck_surface=LearningSurface.SCHEDULER_RUNTIME_ESTIMATOR,
                    evidence=[f"{worst.slice_key} error elevated"],
                    confidence=0.8,
                )
        if placement and not runtime:
            return ImprovementAttributionV1(
                bottleneck_surface=LearningSurface.TASK_PRIORITY_POLICY,
                evidence=["placement accurate; defer"],
                confidence=0.3,
            )
        return None

    def opportunity_from_assessment(
        self, assessment: CapabilitySelfAssessmentV1
    ) -> ImprovementOpportunityV1 | None:
        if assessment.observed_value <= assessment.baseline_value:
            return None
        return ImprovementOpportunityV1(
            learning_surface=assessment.surface,
            summary=f"{assessment.metric_name} miscalibrated on {assessment.slice_key}",
            confidence="STATISTICAL" if assessment.sample_count >= 5 else "SINGLE_CASE_HYPOTHESIS",
        )
