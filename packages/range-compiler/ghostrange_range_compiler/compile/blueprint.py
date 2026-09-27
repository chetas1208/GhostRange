"""TwinBlueprint from normalized graph + sanitization."""

from __future__ import annotations

import hashlib

from ghostrange_contracts.ghost_ir import GhostIRV1
from ghostrange_contracts.system_graph import GraphNodeKind, NormalizedSystemGraphV1
from ghostrange_contracts.twin_compiler import TwinBlueprintV1, TwinSecretSubstitutionV1


def graph_to_ir(graph: NormalizedSystemGraphV1) -> GhostIRV1:
    return GhostIRV1(
        normalized_graph_id=graph.id,
        nodes=[{"name": n.name, "kind": n.kind.value} for n in graph.nodes],
        edges=[{"from": str(e.from_node_id), "to": str(e.to_node_id), "kind": e.kind.value} for e in graph.edges],
        ir_hash=graph.graph_hash,
    )


def build_blueprint(
    ir: GhostIRV1,
    graph: NormalizedSystemGraphV1,
    fidelity_profile_id,
    secret_subs: list[TwinSecretSubstitutionV1],
) -> TwinBlueprintV1:
    services = [n.name for n in graph.nodes if n.kind in (GraphNodeKind.SERVICE, GraphNodeKind.GATEWAY, GraphNodeKind.DATABASE)]
    images = {n.name: n.labels.get("image", "") for n in graph.nodes if n.labels.get("image")}
    bh = hashlib.sha256(((ir.ir_hash or "") + str(len(secret_subs))).encode()).hexdigest()[:16]
    return TwinBlueprintV1(
        ghost_ir_id=ir.id,
        fidelity_profile_id=fidelity_profile_id,
        logical_topology_summary=f"{len(graph.nodes)} nodes, {len(graph.edges)} edges",
        required_services=services,
        service_images=images,
        secret_substitutions=secret_subs,
        blueprint_hash=bh,
    )


__all__ = ["graph_to_ir", "build_blueprint"]
