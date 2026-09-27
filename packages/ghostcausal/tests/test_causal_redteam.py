"""Agent 40 — false causation / confounding scenarios."""

from ghostrange_contracts.ghostcausal_m14 import CausalEdgeStatus
from ghostrange_ghostcausal.discovery import CorrelationHeuristicBackend
from ghostrange_ghostcausal.investigation import CausalInvestigationEngine


def test_correlation_alone_creates_spurious_edges():
    backend = CorrelationHeuristicBackend()
    edges = backend.propose_edges(
        {"GATEWAY_ROUTE": 0.9, "REQUEST_TIMING": 0.88},
        "AUTHORIZATION_BYPASS",
    )
    assert len(edges) >= 2
    for e in edges:
        assert e.status != CausalEdgeStatus.INTERVENTION_SUPPORTED


def test_intervention_refutes_route_hypothesis():
    eng = CausalInvestigationEngine()
    eng.observational_phase()
    eng.run_interventions()
    refuted = any(e.status == CausalEdgeStatus.REFUTED for e in eng.inv.graph.current_revision.edges)
    assert refuted
