"""Agent 09 — structural combination leakage (beyond regex DLP)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ghostrange_contracts.ghostmesh_m13 import MeshContributionV1


@dataclass
class SemanticLeakageReport:
    ok: bool
    risks: list[str] = field(default_factory=list)


def assess_semantic_leakage(c: MeshContributionV1, *, known_local_tags: set[str] | None = None) -> SemanticLeakageReport:
    """Detect rare tag combos that might fingerprint a tenant."""
    risks: list[str] = []
    tags = c.abstract_pattern.abstract_tags
    if len(tags) >= 6 and c.disclosure_level.value != "FEDERATED_AGGREGATE_ONLY":
        risks.append("high_cardinality_tag_set")

    if known_local_tags and set(tags).issubset(known_local_tags) and len(tags) >= 4:
        risks.append("unique_subset_of_local_graph")

    # Specific internal codenames accidentally promoted to tags
    for t in tags:
        if t.lower().endswith("-prod") or "east-" in t.lower():
            risks.append(f"residual_topology_tag:{t}")

    return SemanticLeakageReport(ok=len(risks) == 0, risks=risks)
