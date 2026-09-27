"""Benchmark: three competing auth hypotheses + hidden true mechanism."""

from __future__ import annotations

from uuid import uuid4

from ghostrange_contracts.ghostdirector_m9 import (
    BeliefLevel,
    HypothesisEdgeKind,
    HypothesisGraphEdgeV1,
    HypothesisGraphV1,
    InvestigationHypothesisStatus,
    InvestigationHypothesisV1,
    InvestigationKnowledgeStateV1,
    UncertaintyCategory,
    UncertaintyItemV1,
)


def build_auth_incident_knowledge() -> InvestigationKnowledgeStateV1:
    inv_id = uuid4()
    h1 = InvestigationHypothesisV1(
        investigation_id=inv_id,
        statement="Auth bypass caused by middleware ordering",
        status=InvestigationHypothesisStatus.ACTIVE,
        priority=BeliefLevel.HIGH,
    )
    h2 = InvestigationHypothesisV1(
        investigation_id=inv_id,
        statement="Auth bypass caused by identity cache",
        status=InvestigationHypothesisStatus.ACTIVE,
        priority=BeliefLevel.HIGH,
    )
    h3 = InvestigationHypothesisV1(
        investigation_id=inv_id,
        statement="Auth bypass caused by gateway route configuration",
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
        subject="auth_bypass",
        proposition="Root cause of unauthorized /admin access",
        category=UncertaintyCategory.ATTACK_PATH,
        importance=BeliefLevel.HIGH,
        decision_relevance=BeliefLevel.HIGH,
    )
    return InvestigationKnowledgeStateV1(
        investigation_id=inv_id,
        objective="Explain auth bypass incident in auth-lab",
        hypothesis_graph=graph,
        uncertainties=[u],
        remaining_questions=[
            "Does middleware always run before route handler?",
            "Is identity cache invalidated on role change?",
            "Is gateway routing normalized?",
        ],
    )


def simulate_observation(test_id: str, *, true_mechanism: str) -> dict:
    """Hidden truth: session_refresh_cache (not in initial H1-H3)."""

    if test_id == "middleware_order_probe":
        # Middleware ordering is correct — refutes H1 when mechanism is elsewhere.
        return {"ordering_correct": true_mechanism != "middleware_order", "middleware_first": True, "test_id": test_id}
    if test_id == "gateway_route_probe":
        return {"gateway_misroute": true_mechanism == "gateway_routing", "route_ok": true_mechanism != "gateway_routing", "test_id": test_id}
    if test_id == "full_pcap_redundant":
        return {"noise": True, "test_id": test_id}
    if test_id == "session_refresh_probe":
        return {"session_refresh_bug": true_mechanism == "session_refresh_cache", "test_id": test_id}
    return {"test_id": test_id, "unknown": True}


__all__ = ["build_auth_incident_knowledge", "simulate_observation"]
