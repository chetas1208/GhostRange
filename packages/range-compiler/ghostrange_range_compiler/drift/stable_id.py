"""Deterministic stable entity IDs for drift across revisions."""

from __future__ import annotations

from ghostrange_contracts.system_graph import GraphNodeKind, NormalizedNodeV1


def stable_entity_id(node: NormalizedNodeV1) -> str:
    prov = node.provenance.source_construct or node.name
    return f"{node.kind.value}:{prov}:{node.name}".lower()


__all__ = ["stable_entity_id"]
