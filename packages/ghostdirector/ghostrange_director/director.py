"""GhostDirector — WHAT to test next (not GhostScheduler)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ghostrange_contracts.ghostdirector_m9 import (
    CampaignState,
    DirectorDecisionV1,
    DirectorPolicyId,
    DirectorReasonCode,
    DirectorStopReason,
    DirectorTraceV1,
    ExperimentCampaignBudgetV1,
    ExperimentCampaignV1,
    ExperimentObservationV1,
    ExperimentOperatorKind,
    InvestigationHypothesisStatus,
    InvestigationKnowledgeStateV1,
)

from .dedupe import dedupe_proposals, proposal_fingerprint
from .generate import generate_candidates
from .mechanics import ScenarioMechanics, default_mechanics
from .portfolio import select_portfolio
from .scheduler_bridge import build_execution_dag
from .stopping import should_stop
from .utility import acquisition_score
from .validate import validate_proposal


@dataclass
class GhostDirectorSimulator:
    """Replay benchmark scenarios without Vultr.

    ``mechanics`` selects which incident's content (probes, hidden-mechanism reveal,
    hypothesis-status updates) this simulator plays — see ``mechanics.py``. Leaving it unset
    keeps the original auth-incident scenario (``true_mechanism="session_refresh_cache"``);
    pass ``mechanics=TENANT_ESCALATION_MECHANICS`` (``scenarios/tenant_escalation.py``) together
    with a matching ``true_mechanism`` to run the newer billing/gateway/identity scenario.
    """

    true_mechanism: str = "session_refresh_cache"
    authorized_assets: set[str] = field(default_factory=lambda: {"asset/gw01"})
    trace: DirectorTraceV1 | None = None
    mechanics: ScenarioMechanics | None = None

    def __post_init__(self) -> None:
        if self.mechanics is None:
            self.mechanics = default_mechanics()

    def run_campaign(
        self,
        knowledge: InvestigationKnowledgeStateV1,
        *,
        policy: DirectorPolicyId = DirectorPolicyId.GHOSTDIRECTOR_V1,
        budget: ExperimentCampaignBudgetV1 | None = None,
        max_rounds: int = 5,
    ) -> ExperimentCampaignV1:
        budget = budget or ExperimentCampaignBudgetV1(max_experiments=16, max_compute_usd=20.0)
        campaign_id = uuid4()
        campaign = ExperimentCampaignV1(
            id=campaign_id,
            investigation_id=knowledge.investigation_id,
            policy=policy,
            budget=budget,
            state=CampaignState.ASSESSING,
            knowledge_state=knowledge,
        )
        self.trace = DirectorTraceV1(campaign_id=campaign_id, policy=policy, steps=[])
        experiments_run = 0

        for _round in range(max_rounds):
            stop = should_stop(knowledge, budget, experiments_run=experiments_run, high_priority_unresolved=1)
            if stop:
                campaign.stop_reason = stop
                campaign.state = CampaignState.STOPPED
                break

            raw = generate_candidates(knowledge, mechanics=self.mechanics)
            proposals = dedupe_proposals(raw)
            campaign.proposals.extend(proposals)

            scored = []
            rejected: dict = {}
            selected_ids = []
            for p in proposals:
                vr = validate_proposal(p, authorized_assets=self.authorized_assets, max_cost_usd=budget.remaining_usd)
                if not vr.ok:
                    rejected[p.id] = vr.reason or DirectorReasonCode.UNSAFE_EXPERIMENT
                    continue
                scored.append(acquisition_score(p))

            portfolio = select_portfolio(
                campaign_id,
                proposals,
                scored,
                policy=policy,
                budget_remaining_usd=budget.remaining_usd,
                max_pick=3,
            )

            k_hash = hashlib.sha256(json.dumps(knowledge.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
            decision = DirectorDecisionV1(
                knowledge_state_hash=k_hash,
                candidate_ids=[p.id for p in proposals],
                selected_ids=list(portfolio.selected_proposal_ids),
                rejected_ids=[pid for pid in rejected],
                rejection_reasons={str(k): v for k, v in rejected.items()},
                utility_snapshots=scored,
                policy=policy,
                reason_codes=[DirectorReasonCode.DISCRIMINATES_HYPOTHESES] if portfolio.selected_proposal_ids else [DirectorReasonCode.LOW_VALUE],
            )
            campaign.decisions.append(decision)

            if not portfolio.selected_proposal_ids:
                campaign.stop_reason = DirectorStopReason.NO_HIGH_VALUE_EXPERIMENTS
                campaign.state = CampaignState.STOPPED
                break

            dag = build_execution_dag(campaign_id, portfolio, proposals)
            self.trace.steps.append({"round": _round, "dag_nodes": [str(n) for n in dag.nodes]})

            for pid in portfolio.selected_proposal_ids:
                prop = next(p for p in proposals if p.id == pid)
                op = prop.operators[0]
                test_id = op.parameters.get("test_id", "unknown")
                result = self.mechanics.simulate_observation(test_id, true_mechanism=self.true_mechanism)
                obs = ExperimentObservationV1(
                    experiment_id=pid,
                    world_id=uuid4(),
                    operator_kind=op.kind,
                    observable=test_id,
                    result=result,
                )
                campaign.observations.append(obs)
                experiments_run += 1
                budget.spent_usd += prop.estimated_cost_usd

                self.mechanics.update_knowledge(knowledge, prop, result)
                surprise = self.mechanics.detect_surprise(
                    knowledge,
                    result,
                    observation_id=obs.id,
                    experiment_proposal_objective=prop.objective,
                )
                if surprise:
                    h4 = self.mechanics.propose_hypothesis_from_surprise(knowledge, surprise)
                    h4.status = InvestigationHypothesisStatus.ACTIVE
                    knowledge.hypothesis_graph.hypotheses.append(h4)
                    knowledge.remaining_questions.append(self.mechanics.surprise_followup_question)
                    self.trace.steps.append({"surprise": surprise.suggested_new_hypothesis})

            campaign.knowledge_state = knowledge
            campaign.state = CampaignState.REASSESSING

        if campaign.stop_reason is None:
            campaign.stop_reason = should_stop(knowledge, budget, experiments_run=experiments_run, high_priority_unresolved=0)
        campaign.state = CampaignState.STOPPED
        return campaign


def run_campaign_step(*args, **kwargs) -> ExperimentCampaignV1:
    return GhostDirectorSimulator().run_campaign(*args, **kwargs)


__all__ = ["GhostDirectorSimulator", "run_campaign_step"]
