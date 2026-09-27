"""Load mesh contribution policy from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from ghostrange_contracts.ghostmesh_m13 import KnowledgeClass, MeshContributionPolicyV1, MeshDisclosureLevel


def load_mesh_policy(path: Path) -> MeshContributionPolicyV1:
    raw = yaml.safe_load(path.read_text()) or {}
    classes = [KnowledgeClass(c) for c in raw.get("allowed_knowledge_classes", [])]
    disclosure = MeshDisclosureLevel(raw.get("default_disclosure", "PRIVATE_LOCAL"))
    return MeshContributionPolicyV1(
        sharing_enabled=bool(raw.get("sharing_enabled", False)),
        allowed_knowledge_classes=classes,
        minimum_local_validations=int(raw.get("minimum_local_validations", 1)),
        minimum_abstraction_tags=int(raw.get("minimum_abstraction_tags", 2)),
        default_disclosure=disclosure,
        require_human_approval=bool(raw.get("require_human_approval", True)),
        allowed_federation_ids=list(raw.get("allowed_federation_ids", [])),
        retention_days=int(raw.get("retention_days", 90)),
    )
