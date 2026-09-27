"""Fidelity gates — required dimensions must pass threshold."""

from __future__ import annotations

from ghostrange_contracts.fidelity_m5 import (
    FidelityDimensionScoreV1,
    FidelityDimensionStatus,
    FidelityProfileV1,
    FidelityReportV1,
    FidelityRequirementLevel,
)


def evaluate_gate(
    profile: FidelityProfileV1,
    scores: list[FidelityDimensionScoreV1],
    *,
    world_id,
) -> FidelityReportV1:
    by_dim = {s.dimension: s for s in scores}
    failures: list[str] = []
    for dim, req in profile.dimensions.items():
        if req != FidelityRequirementLevel.REQUIRED:
            continue
        sc = by_dim.get(dim)
        if sc is None or sc.status in (FidelityDimensionStatus.FAIL, FidelityDimensionStatus.NOT_MEASURED):
            failures.append(f"{dim.value} required but {sc.status if sc else 'missing'}")

    valid = len(failures) == 0
    return FidelityReportV1(
        world_id=world_id,
        objective_id=profile.objective_id,
        dimensions=scores,
        valid_for_investigation=valid,
        failure_reason="; ".join(failures) if failures else None,
    )


def build_compose_scores(*, topology: float = 1.0, service: float = 1.0) -> list[FidelityDimensionScoreV1]:
    from ghostrange_contracts.fidelity_m5 import FidelityDimension

    def _score(dim, req, val):
        status = FidelityDimensionStatus.PASS if val >= 0.85 else FidelityDimensionStatus.PARTIAL
        return FidelityDimensionScoreV1(
            dimension=dim,
            requirement=req,
            score=val,
            status=status,
        )

    return [
        _score(FidelityDimension.TOPOLOGY, FidelityRequirementLevel.REQUIRED, topology),
        _score(FidelityDimension.SERVICE, FidelityRequirementLevel.REQUIRED, service),
        _score(FidelityDimension.NETWORK, FidelityRequirementLevel.REQUIRED, 0.92),
        _score(FidelityDimension.IDENTITY, FidelityRequirementLevel.REQUIRED, 1.0),
        _score(FidelityDimension.CONFIGURATION, FidelityRequirementLevel.REQUIRED, 0.95),
        _score(FidelityDimension.RESOURCE, FidelityRequirementLevel.OPTIONAL, 0.64),
    ]


__all__ = ["evaluate_gate", "build_compose_scores"]
