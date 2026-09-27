"""Agent 24 — M8 remote counterexample patterns as bounded search priors."""

from __future__ import annotations

from dataclasses import dataclass

from ghostrange_contracts.ghostmesh_m13 import MeshPriorV1


@dataclass
class SearchFamily:
    family_id: str
    priority: int


def mesh_priors_to_search_families(priors: list[MeshPriorV1]) -> list[SearchFamily]:
    families: list[SearchFamily] = []
    for i, p in enumerate(priors):
        if p.knowledge_class.value != "COUNTEREXAMPLE_PATTERN":
            continue
        fam = "-".join(p.abstract_tags[:3]).lower() or "generic"
        families.append(SearchFamily(family_id=fam, priority=100 - i))
    return sorted(families, key=lambda f: -f.priority)
