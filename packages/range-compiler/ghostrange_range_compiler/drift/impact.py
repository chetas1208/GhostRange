"""Impact propagation from drift over system graph."""

from __future__ import annotations

from uuid import uuid4

from ghostrange_contracts.fidelity_m5 import FidelityDimension, FidelityProfileV1, FidelityRequirementLevel
from ghostrange_contracts.living_twin_m6 import (
    ImpactGraphV1,
    ImpactLevel,
    ImpactRecordV1,
    InvalidationReasonCode,
    SemanticDriftCategory,
)
from ghostrange_contracts.living_twin_m6 import DriftSetV1
from ghostrange_contracts.system_graph import GraphEdgeKind, NormalizedSystemGraphV1

from .stable_id import stable_entity_id

_EDGE_PROPAGATION: dict[str, set[SemanticDriftCategory]] = {
    GraphEdgeKind.DEPENDS_ON.value: {
        SemanticDriftCategory.SERVICE,
        SemanticDriftCategory.VERSION,
        SemanticDriftCategory.CONFIGURATION,
        SemanticDriftCategory.DEPENDENCY,
    },
    GraphEdgeKind.AUTHENTICATES_VIA.value: {
        SemanticDriftCategory.IDENTITY,
        SemanticDriftCategory.CONFIGURATION,
        SemanticDriftCategory.SECURITY_CONTROL,
    },
    GraphEdgeKind.CONNECTS_TO.value: {SemanticDriftCategory.NETWORK, SemanticDriftCategory.TOPOLOGY},
}


def _level_for_category(cat: SemanticDriftCategory, profile: FidelityProfileV1) -> ImpactLevel:
    dim_map = {
        SemanticDriftCategory.IDENTITY: FidelityDimension.IDENTITY,
        SemanticDriftCategory.NETWORK: FidelityDimension.NETWORK,
        SemanticDriftCategory.TOPOLOGY: FidelityDimension.TOPOLOGY,
        SemanticDriftCategory.SERVICE: FidelityDimension.SERVICE,
        SemanticDriftCategory.VERSION: FidelityDimension.VERSION,
        SemanticDriftCategory.CONFIGURATION: FidelityDimension.CONFIGURATION,
        SemanticDriftCategory.RESOURCE: FidelityDimension.RESOURCE,
        SemanticDriftCategory.DATA_SCHEMA: FidelityDimension.DATA_SCHEMA,
    }
    dim = dim_map.get(cat)
    if dim is None:
        return ImpactLevel.UNKNOWN
    req = profile.dimensions.get(dim, FidelityRequirementLevel.OPTIONAL)
    if req == FidelityRequirementLevel.IGNORED:
        return ImpactLevel.NONE
    if req == FidelityRequirementLevel.REQUIRED:
        return ImpactLevel.HIGH
    if req == FidelityRequirementLevel.IMPORTANT:
        return ImpactLevel.MEDIUM
    return ImpactLevel.LOW


def build_impact_graph(
    drift: DriftSetV1,
    graph: NormalizedSystemGraphV1,
    profile: FidelityProfileV1,
    *,
    claim_ids_by_entity: dict[str, list] | None = None,
) -> ImpactGraphV1:
    claim_ids_by_entity = claim_ids_by_entity or {}
    adj: dict[str, list[tuple[str, str]]] = {}
    node_id_to_stable = {n.id: stable_entity_id(n) for n in graph.nodes}
    for e in graph.edges:
        fu = node_id_to_stable.get(e.from_node_id)
        tu = node_id_to_stable.get(e.to_node_id)
        if fu and tu:
            adj.setdefault(fu, []).append((tu, e.kind.value))

    direct: dict[str, ImpactRecordV1] = {}
    for ev in drift.events:
        lvl = _level_for_category(ev.semantic_category, profile)
        if ev.change_type.value == "REMOVE" and ev.entity_name:
            lvl = max_level(lvl, ImpactLevel.CRITICAL)
        direct[ev.stable_entity_id] = ImpactRecordV1(
            entity_id=ev.stable_entity_id,
            entity_name=ev.entity_name,
            level=lvl,
            categories=[ev.semantic_category],
            reason=f"direct drift: {ev.property_path}",
        )

    propagated: dict[str, ImpactRecordV1] = dict(direct)
    for sid, rec in list(direct.items()):
        for cat in rec.categories:
            _propagate(adj, sid, cat, propagated, profile, depth=0, max_depth=4)

    affected_claims = []
    for eid, cids in claim_ids_by_entity.items():
        if eid in propagated and propagated[eid].level not in (ImpactLevel.NONE, ImpactLevel.LOW):
            affected_claims.extend(cids)

    return ImpactGraphV1(
        id=uuid4(),
        drift_set_id=drift.id,
        records=list(propagated.values()),
        affected_claim_ids=affected_claims,
    )


def max_level(a: ImpactLevel, b: ImpactLevel) -> ImpactLevel:
    order = [ImpactLevel.NONE, ImpactLevel.LOW, ImpactLevel.MEDIUM, ImpactLevel.HIGH, ImpactLevel.CRITICAL, ImpactLevel.UNKNOWN]
    return a if order.index(a) >= order.index(b) else b


def _propagate(adj, sid, cat, out, profile, depth, max_depth):
    if depth >= max_depth:
        return
    for target, edge_kind in adj.get(sid, []):
        allowed = _EDGE_PROPAGATION.get(edge_kind, set())
        if cat not in allowed and cat != SemanticDriftCategory.UNKNOWN:
            continue
        lvl = _level_for_category(cat, profile)
        prev = out.get(target)
        if prev:
            lvl = max_level(prev.level, lvl)
            cats = list(set(prev.categories + [cat]))
        else:
            cats = [cat]
        out[target] = ImpactRecordV1(
            entity_id=target,
            entity_name=target.split(":")[-1],
            level=lvl,
            categories=cats,
            reason=f"propagated via {edge_kind} from {sid}",
        )
        _propagate(adj, target, cat, out, profile, depth + 1, max_depth)


__all__ = ["build_impact_graph", "max_level"]
