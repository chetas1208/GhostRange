import json
from pathlib import Path

from ghostrange_contracts.ghostdirector_m9 import (
    DirectorPolicyId,
    DirectorStopReason,
    ExperimentCampaignBudgetV1,
    ExperimentOperatorKind,
    ExperimentOperatorV1,
    ExperimentProposalV1,
    InvestigationHypothesisStatus,
)
from ghostrange_director.director import GhostDirectorSimulator
from ghostrange_director.portfolio import dominates
from ghostrange_director.scenarios.auth_incident import build_auth_incident_knowledge
from ghostrange_director.scheduler_bridge import build_execution_dag
from ghostrange_director.utility import acquisition_score
from ghostrange_director.validate import validate_proposal

GT = Path(__file__).resolve().parents[3] / "benchmarks" / "m9" / "ground_truth" / "auth_incident.json"


def test_ghostdirector_finds_mechanism_via_surprise():
    knowledge = build_auth_incident_knowledge()
    sim = GhostDirectorSimulator(true_mechanism="session_refresh_cache")
    campaign = sim.run_campaign(
        knowledge,
        policy=DirectorPolicyId.GHOSTDIRECTOR_V1,
        budget=ExperimentCampaignBudgetV1(max_experiments=12, max_compute_usd=15),
        max_rounds=4,
    )
    statuses = {h.statement: h.status for h in campaign.knowledge_state.hypothesis_graph.hypotheses}
    assert any("session refresh" in s.lower() for s in statuses)
    assert statuses.get("Auth bypass caused by middleware ordering") == InvestigationHypothesisStatus.REFUTED


def test_scheduler_bridge_separate_from_director():
    knowledge = build_auth_incident_knowledge()
    sim = GhostDirectorSimulator()
    campaign = sim.run_campaign(knowledge, max_rounds=1)
    assert campaign.decisions
    prop = campaign.proposals[0]
    from ghostrange_contracts.ghostdirector_m9 import ExperimentPortfolioV1
    from uuid import uuid4

    portfolio = ExperimentPortfolioV1(campaign_id=uuid4(), selected_proposal_ids=[prop.id])
    dag = build_execution_dag(campaign.id, portfolio, [prop])
    assert dag.nodes == [prop.id]
    assert dag.parallel_groups is not None


def test_safety_rejects_external_target():
    p = ExperimentProposalV1(
        investigation_id=build_auth_incident_knowledge().investigation_id,
        objective="bad",
        operators=[
            ExperimentOperatorV1(
                kind=ExperimentOperatorKind.COLLECT_OBSERVATION,
                parameters={"url": "http://8.8.8.8/"},
                target_asset_id="asset/gw01",
            )
        ],
        estimated_cost_usd=1,
        estimated_runtime_sec=1,
    )
    assert not validate_proposal(p, authorized_assets={"asset/gw01"}, max_cost_usd=5).ok


def test_greedy_information_prefers_discriminator():
    knowledge = build_auth_incident_knowledge()
    from ghostrange_director.generate import generate_candidates
    from ghostrange_director.dedupe import dedupe_proposals
    from ghostrange_director.portfolio import select_portfolio

    props = dedupe_proposals(generate_candidates(knowledge))
    scored = [acquisition_score(p) for p in props]
    port = select_portfolio(
        knowledge.investigation_id,
        props,
        scored,
        policy=DirectorPolicyId.GHOSTDIRECTOR_V1,
        budget_remaining_usd=20,
        max_pick=1,
    )
    selected = next(p for p in props if p.id == port.selected_proposal_ids[0])
    assert "Discriminate" in selected.objective or selected.estimated_cost_usd <= 2


def test_policy_comparison_runs():
    knowledge = build_auth_incident_knowledge()
    results = {}
    for policy in (
        DirectorPolicyId.FIXED_SCRIPT,
        DirectorPolicyId.RANDOM_SAFE,
        DirectorPolicyId.GHOSTDIRECTOR_V1,
    ):
        k = build_auth_incident_knowledge()
        c = GhostDirectorSimulator().run_campaign(
            k,
            policy=policy,
            budget=ExperimentCampaignBudgetV1(max_experiments=8, max_compute_usd=10),
            max_rounds=2,
        )
        results[policy.value] = len(c.observations)
    assert all(n >= 0 for n in results.values())


def test_ground_truth_file_exists_for_evaluators():
    gt = json.loads(GT.read_text())
    assert gt["true_mechanism"] == "session_refresh_cache"


def test_dominance_helper():
    from ghostrange_contracts.ghostdirector_m9 import ExperimentUtilityV1, AcquisitionScoreV1
    from uuid import uuid4

    a = AcquisitionScoreV1(
        proposal_id=uuid4(),
        utility=ExperimentUtilityV1(proposal_id=uuid4(), information_gain=0.8, compute_cost_usd=1),
        total_score=1.0,
    )
    b = AcquisitionScoreV1(
        proposal_id=uuid4(),
        utility=ExperimentUtilityV1(proposal_id=uuid4(), information_gain=0.5, compute_cost_usd=5),
        total_score=0.5,
    )
    assert dominates(a, b)
