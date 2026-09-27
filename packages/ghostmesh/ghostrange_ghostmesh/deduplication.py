"""Agent 15 — content + semantic deduplication via KnowledgeFingerprintV1."""

from __future__ import annotations

import hashlib
import json

from ghostrange_contracts.ghostmesh_m13 import KnowledgeClass, KnowledgeFingerprintV1, MeshContributionV1


def fingerprint_contribution(c: MeshContributionV1) -> KnowledgeFingerprintV1:
    pattern = {
        "class": c.knowledge_class.value,
        "tags": sorted(c.abstract_pattern.abstract_tags),
        "relations": sorted(c.abstract_pattern.abstract_relations),
    }
    abstract_hash = hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()
    fp = hashlib.sha256(f"{c.knowledge_class.value}:{abstract_hash}".encode()).hexdigest()
    return KnowledgeFingerprintV1(
        fingerprint=fp,
        knowledge_class=c.knowledge_class,
        abstract_pattern_hash=abstract_hash,
    )


def is_duplicate(existing: list[MeshContributionV1], incoming: MeshContributionV1) -> bool:
    inc = fingerprint_contribution(incoming)
    for e in existing:
        if fingerprint_contribution(e).fingerprint == inc.fingerprint:
            return True
    return False
