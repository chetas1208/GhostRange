from __future__ import annotations

from uuid import UUID

from ghostrange_contracts.adversarial_m8 import DifferentialObservationV1


def interpret_differential(
    *,
    fingerprint: str,
    baseline_world_id: UUID,
    remediated_world_id: UUID,
    baseline_satisfied: bool,
    remediated_satisfied: bool,
) -> DifferentialObservationV1:
    if baseline_satisfied and remediated_satisfied:
        interpretation = "COUNTEREXAMPLE_CANDIDATE_BOTH_WORLDS"
    elif baseline_satisfied and not remediated_satisfied:
        interpretation = "REMEDIATION_BLOCKS_KNOWN_EXPLOIT"
    elif not baseline_satisfied and remediated_satisfied:
        interpretation = "REGRESSION_OR_INVALID_TEST"
    else:
        interpretation = "NO_FALSIFICATION_ON_EITHER"
    return DifferentialObservationV1(
        candidate_fingerprint=fingerprint,
        baseline_world_id=baseline_world_id,
        remediated_world_id=remediated_world_id,
        baseline_oracle_satisfied=baseline_satisfied,
        remediated_oracle_satisfied=remediated_satisfied,
        interpretation=interpretation,
    )


__all__ = ["interpret_differential"]
