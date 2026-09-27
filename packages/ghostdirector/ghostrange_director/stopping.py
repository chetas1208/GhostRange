from __future__ import annotations

from ghostrange_contracts.ghostdirector_m9 import (
    DirectorStopReason,
    ExperimentCampaignBudgetV1,
    InvestigationHypothesisStatus,
    InvestigationKnowledgeStateV1,
)


def should_stop(
    knowledge: InvestigationKnowledgeStateV1,
    budget: ExperimentCampaignBudgetV1,
    *,
    experiments_run: int,
    high_priority_unresolved: int,
) -> DirectorStopReason | None:
    if budget.spent_usd >= budget.max_compute_usd:
        return DirectorStopReason.BUDGET_EXHAUSTED
    if experiments_run >= budget.max_experiments:
        return DirectorStopReason.BUDGET_EXHAUSTED

    active = [
        h
        for h in knowledge.hypothesis_graph.hypotheses
        if h.status in (InvestigationHypothesisStatus.ACTIVE, InvestigationHypothesisStatus.PROPOSED)
    ]
    supported = [h for h in knowledge.hypothesis_graph.hypotheses if h.status == InvestigationHypothesisStatus.SUPPORTED]

    if len(supported) == 1 and not active:
        return DirectorStopReason.DECISION_SUFFICIENT

    if not active and high_priority_unresolved == 0:
        return DirectorStopReason.UNCERTAINTY_BELOW_POLICY_THRESHOLD

    return None


__all__ = ["should_stop"]
