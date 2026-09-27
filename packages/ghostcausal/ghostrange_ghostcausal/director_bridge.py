"""Agents 15–17 — causal discrimination experiments."""

from __future__ import annotations

from ghostrange_contracts.ghostcausal_m14 import CausalExperimentProposalV1

from .interventions import propose_discrimination_interventions


def propose_causal_experiments(*, competing_mechanisms: list[str]) -> CausalExperimentProposalV1:
    interventions = propose_discrimination_interventions()
    return CausalExperimentProposalV1(
        candidate_mechanisms=competing_mechanisms,
        interventions=interventions,
        identification_objective="discriminate cache-mediated vs route-mediated bypass",
        causal_discrimination_value=0.85,
        cost_usd_estimate=sum(i.cost_usd_estimate for i in interventions),
    )
