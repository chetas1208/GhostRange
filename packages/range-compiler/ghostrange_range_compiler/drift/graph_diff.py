"""Semantic diff of NormalizedSystemGraph — not textual diff."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from ghostrange_contracts.living_twin_m6 import DriftChangeType, DriftEventV1, DriftSetV1
from ghostrange_contracts.system_graph import GraphEdgeKind, NormalizedSystemGraphV1

from .classify import enrich_drift_event
from .stable_id import stable_entity_id


def _node_fingerprint(node) -> str:
    payload = {
        "kind": node.kind.value,
        "labels": node.labels,
        "attributes": node.attributes,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


class SystemGraphDiffEngine:
    def diff(
        self,
        graph_a: NormalizedSystemGraphV1,
        graph_b: NormalizedSystemGraphV1,
        *,
        revision_from,
        revision_to,
    ) -> DriftSetV1:
        return diff_graphs(graph_a, graph_b, revision_from=revision_from, revision_to=revision_to)


def diff_graphs(
    graph_a: NormalizedSystemGraphV1,
    graph_b: NormalizedSystemGraphV1,
    *,
    revision_from,
    revision_to,
) -> DriftSetV1:
    map_a = {stable_entity_id(n): n for n in graph_a.nodes}
    map_b = {stable_entity_id(n): n for n in graph_b.nodes}
    events: list[DriftEventV1] = []

    for sid, node_a in map_a.items():
        node_b = map_b.get(sid)
        if node_b is None:
            events.append(
                enrich_drift_event(
                    DriftEventV1(
                        source_revision_from=revision_from,
                        source_revision_to=revision_to,
                        stable_entity_id=sid,
                        entity_name=node_a.name,
                        property_path="node",
                        change_type=DriftChangeType.REMOVE,
                        old_fingerprint=_node_fingerprint(node_a),
                        provenance=node_a.provenance.source_location,
                    )
                )
            )
            continue
        fp_a, fp_b = _node_fingerprint(node_a), _node_fingerprint(node_b)
        if fp_a != fp_b:
            img_a = node_a.labels.get("image", "")
            img_b = node_b.labels.get("image", "")
            prop = "labels.image" if img_a != img_b else "node.attributes"
            events.append(
                enrich_drift_event(
                    DriftEventV1(
                        source_revision_from=revision_from,
                        source_revision_to=revision_to,
                        stable_entity_id=sid,
                        entity_name=node_a.name,
                        property_path=prop,
                        change_type=DriftChangeType.MODIFY,
                        old_fingerprint=fp_a,
                        new_fingerprint=fp_b,
                        provenance=node_b.provenance.source_location,
                    )
                )
            )

    for sid, node_b in map_b.items():
        if sid not in map_a:
            events.append(
                enrich_drift_event(
                    DriftEventV1(
                        source_revision_from=revision_from,
                        source_revision_to=revision_to,
                        stable_entity_id=sid,
                        entity_name=node_b.name,
                        property_path="node",
                        change_type=DriftChangeType.ADD,
                        new_fingerprint=_node_fingerprint(node_b),
                        provenance=node_b.provenance.source_location,
                    )
                )
            )

    # Edge diff by tuple key
    def edge_key(g: NormalizedSystemGraphV1):
        id_by_node = {n.id: stable_entity_id(n) for n in g.nodes}
        keys = set()
        for e in g.edges:
            fa = id_by_node.get(e.from_node_id, str(e.from_node_id))
            ta = id_by_node.get(e.to_node_id, str(e.to_node_id))
            keys.add((fa, ta, e.kind.value))
        return keys

    ea, eb = edge_key(graph_a), edge_key(graph_b)
    for added in eb - ea:
        ev = DriftEventV1(
            source_revision_from=revision_from,
            source_revision_to=revision_to,
            stable_entity_id=f"edge:{added[0]}->{added[1]}",
            entity_name=f"{added[0]}->{added[1]}",
            property_path=f"edge.{added[2]}",
            change_type=DriftChangeType.ADD,
        )
        events.append(enrich_drift_event(ev))
    for removed in ea - eb:
        events.append(
            DriftEventV1(
                source_revision_from=revision_from,
                source_revision_to=revision_to,
                stable_entity_id=f"edge:{removed[0]}->{removed[1]}",
                entity_name=f"{removed[0]}->{removed[1]}",
                property_path=f"edge.{removed[2]}",
                change_type=DriftChangeType.REMOVE,
            )
        )

    formatting_only = len(events) == 0
    return DriftSetV1(
        id=uuid4(),
        source_revision_from=revision_from,
        source_revision_to=revision_to,
        events=events,
        formatting_only=formatting_only,
    )


__all__ = ["SystemGraphDiffEngine", "diff_graphs"]
