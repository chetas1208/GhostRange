"""Post-deployment verification plans (operator-run in prod; tested in range)."""

from __future__ import annotations

from ghostrange_contracts.ghostgate_m11 import ObservabilityRequirementV1, PostDeploymentVerificationPlanV1


def default_post_change_plan() -> PostDeploymentVerificationPlanV1:
    return PostDeploymentVerificationPlanV1(
        health_checks=["GET /health 200", "auth service ready"],
        security_regressions=["admin header bypass attempt must fail"],
        behavioral_invariants=["legitimate proxy path still authenticates"],
        rollback_triggers=["bypass succeeds", "5xx rate > baseline + 2%"],
    )


def default_observability(*, gap: bool = False) -> ObservabilityRequirementV1:
    signals = ["http_success_rate", "auth_denial_rate", "error_rate", "p95_latency"]
    gaps: list[str] = []
    if gap:
        gaps.append("production lacks auth_denial_rate metric")
    return ObservabilityRequirementV1(signals=signals, gaps=gaps)


def simulate_verification_plan_in_range(plan: PostDeploymentVerificationPlanV1) -> bool:
    return len(plan.health_checks) > 0 and len(plan.security_regressions) > 0
