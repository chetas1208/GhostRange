"""Agent 17 — multidimensional contribution quality (no opaque trust score)."""

from __future__ import annotations

from ghostrange_contracts.ghostmesh_m13 import ContributionQualityV1, MeshContributionV1


def assess_quality(
    c: MeshContributionV1,
    *,
    provenance_valid: bool,
    cross_node_validations: int = 0,
    poisoning_signals: list[str] | None = None,
) -> ContributionQualityV1:
    reason_codes: list[str] = []
    if c.local_validation_count < 1:
        reason_codes.append("LOW_LOCAL_VALIDATIONS")
    if cross_node_validations == 0:
        reason_codes.append("NO_CROSS_NODE_CORROBORATION")
    recency = 1.0  # placeholder — would decay by age in production
    return ContributionQualityV1(
        contribution_id=c.id,
        provenance_valid=provenance_valid,
        local_validations=c.local_validation_count,
        cross_node_validations=cross_node_validations,
        recency_score=recency,
        schema_compatible=True,
        poisoning_signals=poisoning_signals or [],
        reason_codes=reason_codes,
    )
