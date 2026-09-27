"""Agent 29 — membership / property inference probes on model weights."""

from __future__ import annotations

from ghostrange_contracts.ghostmesh_m13 import FederatedPriorModelV1


def membership_inference_probe(model: FederatedPriorModelV1, *, secret_node_feature: str) -> bool:
    """If rank weight key equals secret feature, inferring membership succeeds (attack benchmark)."""
    return secret_node_feature in model.rank_weights


def property_inference_probe(model: FederatedPriorModelV1, *, threshold: float = 0.5) -> bool:
    return any(w >= threshold for w in model.rank_weights.values())
