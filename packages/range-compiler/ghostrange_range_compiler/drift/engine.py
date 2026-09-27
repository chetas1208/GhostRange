"""LivingTwinEngine — revision ingest, diff, impact, revalidation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from ghostrange_contracts.fidelity_m5 import FidelityProfileV1, InvestigationObjectiveV1
from ghostrange_contracts.living_twin_m6 import (
    LivingTwinAnalysisV1,
    SourceRevisionV1,
    SyncDecision,
    SyncPolicyV1,
    TwinRevisionV1,
    TwinRevisionStatus,
    TwinStalenessV1,
    ImpactLevel,
)
from ghostrange_contracts.system_graph import NormalizedSystemGraphV1

from ghostrange_range_compiler.importers.compose import compose_to_graph, parse_compose_file
from ghostrange_range_compiler.fidelity.profile import profile_for_objective

from .graph_diff import diff_graphs
from .impact import build_impact_graph
from .revalidation import build_revalidation_plan


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LivingTwinEngine:
    def __init__(self, *, policy: SyncPolicyV1 | None = None) -> None:
        self.policy = policy or SyncPolicyV1()

    def ingest_revision(self, source_id, path: Path, *, parent: SourceRevisionV1 | None = None) -> SourceRevisionV1:
        return SourceRevisionV1(
            source_id=source_id,
            parent_revision_id=parent.id if parent else None,
            source_hash=_hash_file(path),
            artifact_hashes={path.name: _hash_file(path)},
            source_types=["docker_compose"],
            metadata={"path": str(path)},
        )

    def graph_from_compose(self, path: Path) -> NormalizedSystemGraphV1:
        src = parse_compose_file(path)
        return compose_to_graph(src, path)

    def analyze(
        self,
        graph_a: NormalizedSystemGraphV1,
        graph_b: NormalizedSystemGraphV1,
        rev_a: SourceRevisionV1,
        rev_b: SourceRevisionV1,
        *,
        twin_revision_id,
        objective: InvestigationObjectiveV1 | None = None,
        claim_ids: list | None = None,
        claim_entities: dict[str, list] | None = None,
    ) -> LivingTwinAnalysisV1:
        objective = objective or InvestigationObjectiveV1(
            title="Auth investigation",
            description="Living twin default auth remediation context",
            investigation_kind="auth_remediation",
        )
        profile = profile_for_objective(objective)
        drift = diff_graphs(graph_a, graph_b, revision_from=rev_a.id, revision_to=rev_b.id)
        impact = build_impact_graph(drift, graph_b, profile, claim_ids_by_entity=claim_entities or {})
        staleness = _staleness_from_drift(drift, twin_revision_id)
        sync = _sync_decision(drift, impact, self.policy)
        reval, inc, claim_updates = build_revalidation_plan(
            drift,
            impact,
            claim_ids=claim_ids or [],
            twin_revision_id=twin_revision_id,
            source_revision_id=rev_b.id,
        )
        return LivingTwinAnalysisV1(
            drift=drift,
            impact=impact,
            staleness=staleness,
            sync_decision=sync,
            revalidation=reval,
            incremental=inc,
            claim_updates=claim_updates,
        )


def analyze_revisions(
    path_a: Path,
    path_b: Path,
    *,
    source_id=None,
    claim_ids=None,
) -> LivingTwinAnalysisV1:
    engine = LivingTwinEngine()
    sid = source_id or uuid4()
    rev_a = engine.ingest_revision(sid, path_a)
    rev_b = engine.ingest_revision(sid, path_b, parent=rev_a)
    ga = engine.graph_from_compose(path_a)
    gb = engine.graph_from_compose(path_b)
    twin_rev = TwinRevisionV1(
        twin_id=uuid4(),
        source_revision_id=rev_b.id,
        blueprint_hash=rev_b.source_hash[:16],
        compiler_version="range-compiler/v0.1",
        fidelity_profile_id=profile_for_objective(
            InvestigationObjectiveV1(title="t", description="d", investigation_kind="auth_remediation")
        ).id,
        status=TwinRevisionStatus.CURRENT,
    )
    claim_entities = {}
    if claim_ids:
        for n in gb.nodes:
            if n.name == "auth" or "auth" in n.name.lower():
                from .stable_id import stable_entity_id

                claim_entities[stable_entity_id(n)] = claim_ids
                break
    return engine.analyze(
        ga,
        gb,
        rev_a,
        rev_b,
        twin_revision_id=twin_rev.id,
        claim_ids=claim_ids or [],
        claim_entities=claim_entities,
    )


def _staleness_from_drift(drift, twin_revision_id) -> TwinStalenessV1:
    s = TwinStalenessV1(twin_revision_id=twin_revision_id)
    if drift.formatting_only:
        return s
    for ev in drift.events:
        if ev.semantic_category.value == "IDENTITY":
            s.identity_staleness = max(s.identity_staleness, 0.9)
        if ev.semantic_category.value == "SERVICE":
            s.service_staleness = max(s.service_staleness, 0.8)
        if ev.semantic_category.value == "RESOURCE":
            s.resource_staleness = max(s.resource_staleness, 0.5)
    s.overall_semantic = max(
        s.identity_staleness,
        s.service_staleness,
        s.network_staleness,
        s.config_staleness,
    )
    return s


def _sync_decision(drift, impact, policy: SyncPolicyV1):
    if drift.formatting_only:
        return SyncDecision.IGNORE
    max_lvl = ImpactLevel.NONE
    for r in impact.records:
        if r.level.value == "CRITICAL":
            return policy.critical_impact_decision
        if r.level.value == "HIGH":
            max_lvl = ImpactLevel.HIGH
        elif r.level.value == "UNKNOWN":
            return policy.unknown_impact_on_required_fidelity
    if max_lvl == ImpactLevel.HIGH:
        return policy.high_impact_decision
    return policy.low_impact_decision


__all__ = ["LivingTwinEngine", "analyze_revisions"]
