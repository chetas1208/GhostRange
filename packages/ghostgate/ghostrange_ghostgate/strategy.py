"""Deployment strategy recommendation (plan only)."""

from __future__ import annotations

from ghostrange_contracts.ghostgate_m11 import (
    CanaryPlanV1,
    CanaryStageV1,
    ChangeRiskProfileV1,
    DeploymentStrategyKind,
    DeploymentStrategyV1,
    RiskLevel,
)


def recommend_strategy(risk: ChangeRiskProfileV1) -> DeploymentStrategyV1:
    if risk.identity_impact == RiskLevel.HIGH and risk.data_impact == RiskLevel.NONE:
        canary = CanaryPlanV1(
            stages=[
                CanaryStageV1(
                    stage_index=0,
                    traffic_percentage=10,
                    duration_minutes=15,
                    success_conditions=["auth_denial_rate stable", "no elevated 5xx"],
                    failure_conditions=["auth bypass regression", "error rate spike"],
                ),
                CanaryStageV1(
                    stage_index=1,
                    traffic_percentage=50,
                    duration_minutes=30,
                    success_conditions=["security invariants hold"],
                    failure_conditions=["rollback trigger fired"],
                ),
                CanaryStageV1(
                    stage_index=2,
                    traffic_percentage=100,
                    duration_minutes=60,
                    success_conditions=["post-change verification pass"],
                    failure_conditions=["manual abort"],
                ),
            ],
            rollback_trigger=["health invariant fails", "auth bypass detected"],
        )
        return DeploymentStrategyV1(
            kind=DeploymentStrategyKind.CANARY,
            rationale="Identity-path change with reversible config; high security impact.",
            canary=canary,
        )
    if risk.data_impact == RiskLevel.HIGH:
        return DeploymentStrategyV1(
            kind=DeploymentStrategyKind.MANUAL_SEQUENCE,
            rationale="Schema/data change requires manual staged rollout.",
        )
    return DeploymentStrategyV1(
        kind=DeploymentStrategyKind.ROLLING,
        rationale="Low blast radius config change.",
    )
