"""Revalidation and incremental compile plans."""

from __future__ import annotations

from uuid import uuid4

from ghostrange_contracts.living_twin_m6 import (
    ClaimValidityStatus,
    ClaimValidityV1,
    DriftSetV1,
    ImpactGraphV1,
    ImpactLevel,
    IncrementalAction,
    IncrementalCompilationPlanV1,
    InvalidationReasonCode,
    RevalidationPlanV1,
    SemanticDriftCategory,
)


def build_revalidation_plan(
    drift: DriftSetV1,
    impact: ImpactGraphV1,
    *,
    claim_ids: list,
    twin_revision_id,
    source_revision_id,
) -> tuple[RevalidationPlanV1, IncrementalCompilationPlanV1, list[ClaimValidityV1]]:
    if drift.formatting_only:
        plan = RevalidationPlanV1(
            drift_set_id=drift.id,
            impact_graph_id=impact.id,
            unaffected_claim_ids=claim_ids,
        )
        inc = IncrementalCompilationPlanV1(
            twin_revision_from=twin_revision_id,
            actions=[IncrementalAction.NOOP],
        )
        validity = [
            ClaimValidityV1(
                claim_id=cid,
                status=ClaimValidityStatus.CURRENT,
                twin_revision_id=twin_revision_id,
                source_revision_id=source_revision_id,
            )
            for cid in claim_ids
        ]
        return plan, inc, validity

    high_entities = [r.entity_id for r in impact.records if r.level in (ImpactLevel.HIGH, ImpactLevel.CRITICAL, ImpactLevel.UNKNOWN)]
    tests = []
    if any(
        ev.semantic_category
        in (
            SemanticDriftCategory.IDENTITY,
            SemanticDriftCategory.VERSION,
            SemanticDriftCategory.SERVICE,
            SemanticDriftCategory.CONFIGURATION,
        )
        or "auth" in ev.entity_name.lower()
        for ev in drift.events
    ):
        tests.extend(["auth_invariants", "attack_replay", "auth_regression"])

    affected = list(set(impact.affected_claim_ids))
    auth_drift = any("auth" in ev.entity_name.lower() for ev in drift.events)
    if auth_drift and claim_ids:
        affected = list(set(affected) | set(claim_ids))
    elif not affected and high_entities and claim_ids:
        affected = list(claim_ids)
    unaffected = [c for c in claim_ids if c not in affected]

    inc_actions = [IncrementalAction.NOOP]
    full_rebuild = any(ev.change_type.value == "REMOVE" for ev in drift.events if "auth" in ev.entity_name.lower())
    if full_rebuild:
        inc_actions = [IncrementalAction.REBUILD_WORLD]
    elif high_entities:
        inc_actions = [IncrementalAction.REBUILD_CONTAINER, IncrementalAction.RESTART_SERVICE]

    plan = RevalidationPlanV1(
        id=uuid4(),
        drift_set_id=drift.id,
        impact_graph_id=impact.id,
        affected_components=high_entities,
        fidelity_checks=["topology", "identity"] if tests else [],
        verification_tests=tests,
        claims_awaiting=affected,
        unaffected_claim_ids=unaffected,
    )
    inc = IncrementalCompilationPlanV1(
        id=uuid4(),
        twin_revision_from=twin_revision_id,
        actions=inc_actions,
        affected_entity_ids=high_entities,
        full_rebuild_required=full_rebuild,
        reason="FULL_REBUILD_REQUIRED" if full_rebuild else "selective",
    )

    validity: list[ClaimValidityV1] = []
    for cid in unaffected:
        validity.append(
            ClaimValidityV1(
                claim_id=cid,
                status=ClaimValidityStatus.CURRENT,
                twin_revision_id=twin_revision_id,
                source_revision_id=source_revision_id,
            )
        )
    for cid in affected:
        validity.append(
            ClaimValidityV1(
                claim_id=cid,
                status=ClaimValidityStatus.STALE,
                twin_revision_id=twin_revision_id,
                source_revision_id=source_revision_id,
                reason_codes=[InvalidationReasonCode.SOURCE_PROPERTY_CHANGED],
                explanation="Drift impact requires revalidation before CURRENT",
            )
        )
    return plan, inc, validity


__all__ = ["build_revalidation_plan"]
