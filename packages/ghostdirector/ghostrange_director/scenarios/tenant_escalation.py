"""Golden-path scenario #2: cross-tenant billing-data exposure via config drift.

Incident narrative ("ghostrange-tenant-escalation-v1" / "privesc-incident-047")
--------------------------------------------------------------------------------
A low-privilege, single-tenant billing viewer somehow received another tenant's invoice and
usage data from ``GET /billing/export``. Three competing hypotheses are opened, each pointing
at a *different* service in the platform (not three flavors of the same cache bug):

  H1  billing-service    — the export endpoint itself may be missing a tenant-scope check
                            (IDOR: trusts a caller-supplied ``tenant_id`` without verifying it
                            against the caller's own tenant claim).
  H2  api-gateway        — the gateway may be accepting an unverified ``role`` claim from a
                            second, newer JWT issuer introduced for a mid-migration window,
                            without checking that issuer's signature the same way as the
                            primary one (classic algorithm/issuer-confusion).
  H3  identity-service    — the RBAC role cache may not invalidate immediately when a tenant
                            admin is demoted, leaving a short window where the old, elevated
                            role is still served from cache.

Hidden true mechanism (never in H1-H3, only reachable via GhostDirector's surprise path):
``internal_role_header_trust`` — during a canary deploy, the gateway's nginx template
regressed and stopped stripping the internal-only ``X-Internal-Role`` header for *external*
traffic, and billing-service's legacy ``TRUST_INTERNAL_ROLE_HEADER`` debug flag (meant only for
service-mesh-internal, mTLS-authenticated calls) was never removed. Two independent trust
leftovers, neither visible from H1-H3, combine into the real exploit — the kind of
supply-chain-style config drift real incident reviews actually turn up, not a guessable
variant of the three initial theories.

This module supplies the ``ScenarioMechanics`` GhostDirectorSimulator needs to run this
scenario — see ``mechanics.py`` for the seam. It intentionally mirrors the *structure* of
``auth_incident.py`` (discriminator probe -> per-hypothesis probe -> decoy -> hidden probe)
so the generic director/generate/portfolio code needs no per-scenario special-casing; only the
probes' names/targets/asset-scope are new content.

Sizing note (multi-worker live mode): this scenario's independently-runnable units are the 3
hypothesis probes (billing-service, api-gateway, identity-service — each its own
``target_asset_id``, so validated as separate authorized assets, not one shared "asset/gw01"),
the hidden-mechanism probe once revealed, and the two adversarial remediation candidates in
``ghostrange_adversarial.scenarios.billing_export_lab`` (shallow fix vs. deep fix, each its own
search world). That is up to ~6 independently schedulable experiment/world units across a
2-round campaign — sized for, but not padded to, a live run using several real workers in
parallel; a smaller live run naturally uses fewer.
"""

from __future__ import annotations

from uuid import uuid4

from ghostrange_contracts.ghostdirector_m9 import (
    BeliefLevel,
    ExperimentOperatorKind,
    HypothesisEdgeKind,
    HypothesisGraphEdgeV1,
    HypothesisGraphV1,
    InvestigationHypothesisStatus,
    InvestigationHypothesisV1,
    InvestigationKnowledgeStateV1,
    SurpriseObservationV1,
    UncertaintyCategory,
    UncertaintyItemV1,
)

from ..mechanics import ProbeSpec, ScenarioMechanics

# Hypothesis "type" tags used to route probe results to the right hypothesis, instead of
# brittle substring-matching over free-text statements (what the original auth-incident
# scenario does). Each hypothesis in this scenario carries one of these.
BILLING_SERVICE_IDOR = "billing_service_idor"
GATEWAY_JWT_CLAIM_CONFUSION = "gateway_jwt_claim_confusion"
IDENTITY_RBAC_CACHE_STALENESS = "identity_rbac_cache_staleness"
INTERNAL_ROLE_HEADER_TRUST = "internal_role_header_trust"

TRUE_MECHANISM = INTERNAL_ROLE_HEADER_TRUST


def build_tenant_escalation_knowledge() -> InvestigationKnowledgeStateV1:
    inv_id = uuid4()
    h1 = InvestigationHypothesisV1(
        investigation_id=inv_id,
        statement=(
            "Cross-tenant billing data exposure via missing tenant-scope check in the "
            "billing-service export endpoint (IDOR)"
        ),
        hypothesis_type=BILLING_SERVICE_IDOR,
        status=InvestigationHypothesisStatus.ACTIVE,
        priority=BeliefLevel.HIGH,
    )
    h2 = InvestigationHypothesisV1(
        investigation_id=inv_id,
        statement=(
            "Cross-tenant billing data exposure via an unverified role claim trusted by the "
            "API gateway from the JWT-issuer migration path"
        ),
        hypothesis_type=GATEWAY_JWT_CLAIM_CONFUSION,
        status=InvestigationHypothesisStatus.ACTIVE,
        priority=BeliefLevel.HIGH,
    )
    h3 = InvestigationHypothesisV1(
        investigation_id=inv_id,
        statement=(
            "Cross-tenant billing data exposure via a stale RBAC role cache in "
            "identity-service after a tenant-admin demotion"
        ),
        hypothesis_type=IDENTITY_RBAC_CACHE_STALENESS,
        status=InvestigationHypothesisStatus.ACTIVE,
        priority=BeliefLevel.MEDIUM,
    )
    graph = HypothesisGraphV1(
        investigation_id=inv_id,
        hypotheses=[h1, h2, h3],
        edges=[
            HypothesisGraphEdgeV1(from_hypothesis_id=h1.id, to_hypothesis_id=h2.id, kind=HypothesisEdgeKind.COMPETES_WITH),
            HypothesisGraphEdgeV1(from_hypothesis_id=h2.id, to_hypothesis_id=h3.id, kind=HypothesisEdgeKind.COMPETES_WITH),
        ],
    )
    u = UncertaintyItemV1(
        subject="tenant_data_exposure",
        proposition="Root cause of cross-tenant billing export exposure",
        category=UncertaintyCategory.ATTACK_PATH,
        importance=BeliefLevel.HIGH,
        decision_relevance=BeliefLevel.HIGH,
    )
    return InvestigationKnowledgeStateV1(
        investigation_id=inv_id,
        objective="Explain cross-tenant billing export exposure in the billing platform lab",
        hypothesis_graph=graph,
        uncertainties=[u],
        remaining_questions=[
            "Does billing-service verify the JWT tenant claim against the requested tenant_id on every export?",
            "Does the API gateway cryptographically verify role claims for every JWT issuer, including the migration issuer?",
            "Is the identity-service RBAC cache invalidated immediately on a tenant-admin demotion?",
        ],
    )


def simulate_observation(test_id: str, *, true_mechanism: str) -> dict:
    """Hidden truth: internal_role_header_trust (not representable by H1-H3)."""

    if test_id == "tenant_scope_probe":
        # billing-service's own tenant-scope check is fine — refutes H1 when mechanism is elsewhere.
        return {"tenant_scope_enforced": true_mechanism != BILLING_SERVICE_IDOR, "test_id": test_id}
    if test_id == "jwt_claim_probe":
        return {"jwt_claim_verified": true_mechanism != GATEWAY_JWT_CLAIM_CONFUSION, "test_id": test_id}
    if test_id == "full_pcap_redundant":
        return {"noise": True, "test_id": test_id}
    if test_id == "internal_role_header_probe":
        return {
            "internal_role_header_trusted": true_mechanism == INTERNAL_ROLE_HEADER_TRUST,
            "test_id": test_id,
        }
    return {"test_id": test_id, "unknown": True}


def update_knowledge(knowledge: InvestigationKnowledgeStateV1, prop, result: dict) -> None:
    if result.get("tenant_scope_enforced"):
        for h in knowledge.hypothesis_graph.hypotheses:
            if h.hypothesis_type == BILLING_SERVICE_IDOR:
                h.status = InvestigationHypothesisStatus.REFUTED
    if result.get("jwt_claim_verified"):
        for h in knowledge.hypothesis_graph.hypotheses:
            if h.hypothesis_type == GATEWAY_JWT_CLAIM_CONFUSION:
                h.status = InvestigationHypothesisStatus.WEAKENED
    if result.get("internal_role_header_trusted"):
        for h in knowledge.hypothesis_graph.hypotheses:
            if h.hypothesis_type == INTERNAL_ROLE_HEADER_TRUST:
                h.status = InvestigationHypothesisStatus.SUPPORTED
    if result.get("tenant_scope_enforced") and result.get("jwt_claim_verified"):
        for h in knowledge.hypothesis_graph.hypotheses:
            if h.hypothesis_type == IDENTITY_RBAC_CACHE_STALENESS and h.status == InvestigationHypothesisStatus.ACTIVE:
                h.status = InvestigationHypothesisStatus.UNRESOLVED


def detect_surprise(
    knowledge: InvestigationKnowledgeStateV1,
    observation: dict,
    *,
    observation_id,
    experiment_proposal_objective: str,
) -> SurpriseObservationV1 | None:
    if observation.get("tenant_scope_enforced") and observation.get("test_id") == "tenant_scope_probe":
        active = [h for h in knowledge.hypothesis_graph.hypotheses if h.status == InvestigationHypothesisStatus.ACTIVE]
        if any(h.hypothesis_type == INTERNAL_ROLE_HEADER_TRUST for h in knowledge.hypothesis_graph.hypotheses):
            return None
        return SurpriseObservationV1(
            observation_id=observation_id,
            unpredicted_by_hypothesis_ids=[h.id for h in active],
            suggested_new_hypothesis=(
                "Internal-role header trust boundary bypassed after canary config drift "
                "(gateway stopped stripping X-Internal-Role for external traffic; "
                "billing-service's legacy internal-role-trust flag was never removed)"
            ),
        )
    return None


def propose_hypothesis_from_surprise(
    knowledge: InvestigationKnowledgeStateV1,
    surprise: SurpriseObservationV1,
) -> InvestigationHypothesisV1:
    return InvestigationHypothesisV1(
        investigation_id=knowledge.investigation_id,
        statement=surprise.suggested_new_hypothesis or "Unknown mechanism (OTHER)",
        hypothesis_type=INTERNAL_ROLE_HEADER_TRUST,
        status=InvestigationHypothesisStatus.PROPOSED,
    )


TENANT_ESCALATION_MECHANICS = ScenarioMechanics(
    simulate_observation=simulate_observation,
    update_knowledge=update_knowledge,
    detect_surprise=detect_surprise,
    propose_hypothesis_from_surprise=propose_hypothesis_from_surprise,
    discriminate_probe=ProbeSpec(
        test_id="tenant_scope_probe",
        operator_kind=ExperimentOperatorKind.COLLECT_OBSERVATION,
        objective="Discriminate {h1} vs {h2}",
        target_asset_id="asset/billing01",
        cost_usd=0.5,
        runtime_sec=30,
        discriminating_power=BeliefLevel.HIGH,
        discriminate_observation_key="tenant_scope_enforced",
    ),
    per_hypothesis_probe=ProbeSpec(
        test_id="jwt_claim_probe",
        operator_kind=ExperimentOperatorKind.COLLECT_OBSERVATION,
        objective="API-gateway JWT claim-verification probe for hypothesis {hid}",
        target_asset_id="asset/gw01",
        cost_usd=1.0,
        runtime_sec=60,
        discriminating_power=BeliefLevel.MEDIUM,
    ),
    hidden_probe=ProbeSpec(
        test_id="internal_role_header_probe",
        operator_kind=ExperimentOperatorKind.APPLY_CONTROLLED_CONFIG_VARIATION,
        objective="Internal-role header trust-boundary probe (post-canary config-drift check)",
        target_asset_id="asset/gw01",
        cost_usd=0.9,
        runtime_sec=40,
        discriminating_power=BeliefLevel.HIGH,
        matches=lambda h: getattr(h, "hypothesis_type", "") == INTERNAL_ROLE_HEADER_TRUST,
    ),
    surprise_followup_question="Internal-role header trust boundary interaction with billing-service's debug flag?",
)


__all__ = [
    "build_tenant_escalation_knowledge",
    "simulate_observation",
    "update_knowledge",
    "detect_surprise",
    "propose_hypothesis_from_surprise",
    "TENANT_ESCALATION_MECHANICS",
    "TRUE_MECHANISM",
    "BILLING_SERVICE_IDOR",
    "GATEWAY_JWT_CLAIM_CONFUSION",
    "IDENTITY_RBAC_CACHE_STALENESS",
    "INTERNAL_ROLE_HEADER_TRUST",
]
