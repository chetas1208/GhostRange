"""Translate Director portfolio → execution DAG for GhostScheduler (separate system)."""

from __future__ import annotations

from ghostrange_contracts.ghostdirector_m9 import (
    ExperimentExecutionDAGV1,
    ExperimentPortfolioV1,
    ExperimentProposalV1,
)


def build_execution_dag(
    campaign_id,
    portfolio: ExperimentPortfolioV1,
    proposals: list[ExperimentProposalV1],
) -> ExperimentExecutionDAGV1:
    by_id = {p.id: p for p in proposals}
    edges: list[tuple] = []
    for pid in portfolio.selected_proposal_ids:
        p = by_id.get(pid)
        if not p:
            continue
        for dep in p.depends_on_experiment_ids:
            if dep in portfolio.selected_proposal_ids:
                edges.append((dep, pid))
    return ExperimentExecutionDAGV1(
        campaign_id=campaign_id,
        nodes=list(portfolio.selected_proposal_ids),
        edges=edges,
        parallel_groups=portfolio.parallel_groups,
    )


__all__ = ["build_execution_dag"]
