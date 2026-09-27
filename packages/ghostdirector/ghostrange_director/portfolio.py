from __future__ import annotations

from ghostrange_contracts.ghostdirector_m9 import (
    AcquisitionScoreV1,
    DirectorPolicyId,
    ExperimentPortfolioV1,
    ExperimentProposalV1,
)


def dominates(a: AcquisitionScoreV1, b: AcquisitionScoreV1) -> bool:
    ua, ub = a.utility, b.utility
    if ua.compute_cost_usd > ub.compute_cost_usd:
        return False
    return (
        ua.information_gain >= ub.information_gain
        and ua.decision_relevance >= ub.decision_relevance
        and a.total_score >= b.total_score
        and (ua.compute_cost_usd < ub.compute_cost_usd or a.total_score > b.total_score)
    )


def prune_dominated(scored: list[AcquisitionScoreV1]) -> list[AcquisitionScoreV1]:
    keep: list[AcquisitionScoreV1] = []
    for a in scored:
        if any(dominates(b, a) for b in scored if b.proposal_id != a.proposal_id):
            continue
        keep.append(a)
    return keep


def select_portfolio(
    campaign_id,
    proposals: list[ExperimentProposalV1],
    scored: list[AcquisitionScoreV1],
    *,
    policy: DirectorPolicyId,
    budget_remaining_usd: float,
    max_pick: int = 3,
) -> ExperimentPortfolioV1:
    by_id = {p.id: p for p in proposals}
    ordered = sorted(scored, key=lambda s: s.total_score, reverse=True)

    if policy == DirectorPolicyId.FIXED_SCRIPT:
        ordered = sorted(scored, key=lambda s: str(s.proposal_id))
    elif policy == DirectorPolicyId.RANDOM_SAFE:
        import random

        random.shuffle(ordered)
    elif policy == DirectorPolicyId.GREEDY_INFORMATION:
        ordered = sorted(scored, key=lambda s: s.utility.information_gain, reverse=True)
    elif policy == DirectorPolicyId.GREEDY_DECISION_VALUE:
        ordered = sorted(scored, key=lambda s: s.utility.decision_relevance, reverse=True)

    ordered = prune_dominated(ordered)
    selected: list = []
    parallel: list[list] = []
    cost_map: dict[str, float] = {}
    total_cost = 0.0

    for s in ordered:
        if len(selected) >= max_pick:
            break
        p = by_id.get(s.proposal_id)
        if not p:
            continue
        if total_cost + p.estimated_cost_usd > budget_remaining_usd:
            continue
        deps_ok = all(d in selected for d in p.depends_on_experiment_ids)
        if not deps_ok:
            continue
        selected.append(p.id)
        total_cost += p.estimated_cost_usd
        cost_map[str(p.id)] = p.estimated_cost_usd
        if p.parallelizable:
            if parallel and len(parallel[-1]) < 2:
                parallel[-1].append(p.id)
            else:
                parallel.append([p.id])
        else:
            parallel.append([p.id])

    return ExperimentPortfolioV1(
        campaign_id=campaign_id,
        selected_proposal_ids=selected,
        parallel_groups=parallel,
        budget_allocation_usd=cost_map,
        expected_aggregate_value=sum(s.total_score for s in ordered if s.proposal_id in selected),
    )


__all__ = ["select_portfolio", "prune_dominated", "dominates"]
