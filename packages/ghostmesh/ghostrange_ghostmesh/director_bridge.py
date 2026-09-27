"""Inject Mesh priors into experiment ordering — never conclusions."""

from __future__ import annotations

from dataclasses import dataclass

from ghostrange_contracts.ghostmesh_m13 import ApplicabilityResult, MeshPriorV1


@dataclass
class PrioritizedExperiment:
    test_id: str
    title: str
    mesh_boost: float
    origin: str


def prioritize_with_mesh_priors(
    base_experiments: list[PrioritizedExperiment],
    priors: list[MeshPriorV1],
    applicability: ApplicabilityResult,
    *,
    exploration_reserve: float = 0.2,
) -> list[PrioritizedExperiment]:
    """Reorder local experiments; reserve budget for novel hypotheses."""
    if applicability == ApplicabilityResult.NOT_APPLICABLE:
        return base_experiments

    boost = 0.35 if applicability == ApplicabilityResult.APPLICABLE else 0.15
    if not priors:
        return base_experiments

    mesh_first = PrioritizedExperiment(
        test_id="session_refresh_identity_probe",
        title="Mesh prior: session refresh + cached identity interaction",
        mesh_boost=boost,
        origin="MESH_PRIOR",
    )
    capped_boost = min(boost, 1.0 - exploration_reserve)
    mesh_first.mesh_boost = capped_boost

    rest = [e for e in base_experiments if e.test_id != mesh_first.test_id]
    return [mesh_first, *rest]
