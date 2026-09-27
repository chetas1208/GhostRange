from ghostrange_contracts.ghostcausal_m14 import (
    CausalEdgeStatus,
    CausalValidityStatus,
    TransportabilityQueryV1,
    TransportabilityStatus,
)
from ghostrange_ghostcausal.investigation import CausalInvestigationEngine
from ghostrange_ghostcausal.simulator import run_m14_flagship_demo
from ghostrange_ghostcausal.transport import analyze_transport, structural_match_would_transfer


def test_interventions_support_cache_not_route():
    eng = CausalInvestigationEngine()
    eng.observational_phase()
    results = eng.run_interventions()
    assert results["CACHE_INVALIDATED"] is False
    assert results["ROUTE_CHANGED"] is True
    rc = eng.root_cause_report()
    assert rc.validity == CausalValidityStatus.INTERVENTION_SUPPORTED
    assert "STALE_CACHE" in rc.supported_causes or "SESSION_REFRESH" in rc.supported_causes


def test_counterfactual_corroboration():
    eng = CausalInvestigationEngine()
    _, val = eng.counterfactual()
    assert val.experimental_corroboration is True


def test_transport_C_not_transportable_while_structural_match():
    q = TransportabilityQueryV1(source_domain="A", target_domain="C", causal_query="bypass mechanism")
    rep = analyze_transport(q)
    assert rep.status == TransportabilityStatus.NOT_TRANSPORTABLE
    assert structural_match_would_transfer("C")


def test_flagship_demo():
    d = run_m14_flagship_demo()
    assert d["m14_rejects_C_transport"]
    assert d["cache_blocks_bypass"]
