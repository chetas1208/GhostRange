from uuid import uuid4

from ghostrange_contracts.ghostdirector_m9 import (
    BeliefLevel,
    ExperimentProposalV1,
    ExperimentOperatorV1,
    ExperimentOperatorKind,
    InvestigationKnowledgeStateV1,
    HypothesisGraphV1,
)


def test_experiment_proposal_requires_operator():
    p = ExperimentProposalV1(
        investigation_id=uuid4(),
        objective="probe",
        operators=[ExperimentOperatorV1(kind=ExperimentOperatorKind.COLLECT_OBSERVATION)],
        estimated_cost_usd=1.0,
        estimated_runtime_sec=10.0,
    )
    assert p.operators[0].kind == ExperimentOperatorKind.COLLECT_OBSERVATION


def test_knowledge_state_minimal():
    inv = uuid4()
    ks = InvestigationKnowledgeStateV1(
        investigation_id=inv,
        objective="test",
        hypothesis_graph=HypothesisGraphV1(investigation_id=inv),
    )
    assert ks.objective == "test"
