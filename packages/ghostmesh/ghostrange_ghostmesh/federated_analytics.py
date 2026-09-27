"""Agent 27 — privacy-aware aggregate statistics."""

from __future__ import annotations

from ghostrange_contracts.ghostmesh_m13 import KnowledgeClass

from .differential_privacy import noisy_count
from .registry import MeshKnowledgeRegistry


def cohort_validation_rate(
    registry: MeshKnowledgeRegistry,
    kclass: KnowledgeClass,
    *,
    min_cohort: int,
    epsilon: float = 1.0,
) -> dict | None:
    items = [c for c in registry.contributions.values() if c.knowledge_class == kclass]
    if len(items) < min_cohort:
        return None
    successes = sum(1 for c in items if c.failure_count == 0)
    rate = successes / max(1, len(items))
    noisy_n, budget = noisy_count(len(items), epsilon=epsilon, delta=1e-5, scope=f"cohort:{kclass.value}")
    return {
        "knowledge_class": kclass.value,
        "validation_rate": round(rate, 3),
        "cohort_size_noisy": noisy_n,
        "privacy_budget": budget.model_dump(mode="json"),
        "minimum_cohort_met": len(items) >= min_cohort,
    }
