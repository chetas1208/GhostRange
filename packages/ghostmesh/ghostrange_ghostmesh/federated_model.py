"""Agent 28 — experimental FederatedPriorModelV1 (rank experiments only)."""

from __future__ import annotations

from ghostrange_contracts.ghostmesh_m13 import FederatedPriorModelV1, MeshPriorV1


def rank_test_ids(priors: list[MeshPriorV1], candidates: list[str]) -> list[str]:
    weights: dict[str, float] = {}
    for p in priors:
        for tag in p.abstract_tags:
            key = tag.lower().replace("_", "-")
            weights[key] = weights.get(key, 0.0) + p.exploration_weight

    def score(test_id: str) -> float:
        s = 0.0
        for k, w in weights.items():
            if k.replace("-", "") in test_id.replace("_", ""):
                s += w
        return s

    return sorted(candidates, key=lambda t: -score(t))


def build_model(*, round_id: int, priors: list[MeshPriorV1]) -> FederatedPriorModelV1:
    rank_weights = {p.applicability_hint or "prior": p.exploration_weight for p in priors}
    return FederatedPriorModelV1(
        model_id=f"federated-prior-{round_id}",
        training_round=round_id,
        rank_weights=rank_weights,
    )
