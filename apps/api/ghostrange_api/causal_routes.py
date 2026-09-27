from fastapi import APIRouter
from ghostrange_contracts.ghostcausal_m14 import TransportabilityQueryV1
from ghostrange_ghostcausal.investigation import CausalInvestigationEngine
from ghostrange_ghostcausal.simulator import run_m14_flagship_demo
from ghostrange_ghostcausal.transport import analyze_transport

router = APIRouter(prefix="/v1/causal", tags=["causal"])

_engine = CausalInvestigationEngine()


@router.post("/investigation/run")
async def run_investigation():
    _engine.observational_phase()
    results = _engine.run_interventions()
    rc = _engine.root_cause_report()
    claim = _engine.causal_claim()
    cf, cf_val = _engine.counterfactual()
    return {
        "label": "SIMULATED_SCM",
        "interventions": results,
        "root_cause": rc.model_dump(mode="json"),
        "claim": claim.model_dump(mode="json"),
        "counterfactual": cf.model_dump(mode="json"),
        "counterfactual_validity": cf_val.model_dump(mode="json"),
    }


@router.post("/transport/analyze")
async def transport_analyze(source: str = "A", target: str = "C"):
    q = TransportabilityQueryV1(source_domain=source, target_domain=target, causal_query="auth bypass mechanism")
    return analyze_transport(q).model_dump(mode="json")


@router.post("/demo/flagship")
async def flagship_demo():
    return run_m14_flagship_demo()
