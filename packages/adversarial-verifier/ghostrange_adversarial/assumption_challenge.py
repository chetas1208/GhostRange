from __future__ import annotations

from ghostrange_contracts.adversarial_m8 import AssumptionChallengeV1
from ghostrange_contracts.living_twin_m6 import AssumptionV1


def challenge_assumption(assumption: AssumptionV1) -> AssumptionChallengeV1:
    return AssumptionChallengeV1(
        assumption_id=assumption.id,
        challenge_strategy="negate_assumption_predicate",
        required_world_state={"focus": assumption.property_path or "unknown"},
        actions=[{"type": "probe_assumption", "path": assumption.property_path}],
        expected_violation_condition=f"assumption_{assumption.id}_may_not_hold",
    )


__all__ = ["challenge_assumption"]
