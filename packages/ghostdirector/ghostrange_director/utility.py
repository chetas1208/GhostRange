"""Experiment valuation — no fake probability percentages."""

from __future__ import annotations

from ghostrange_contracts.ghostdirector_m9 import (
    AcquisitionScoreV1,
    BeliefLevel,
    ExperimentProposalV1,
    ExperimentUtilityV1,
)


def _level_to_float(level: BeliefLevel) -> float:
    return {"UNKNOWN": 0.1, "LOW": 0.35, "MEDIUM": 0.6, "HIGH": 0.85}[level.value]


def estimate_utility(proposal: ExperimentProposalV1) -> ExperimentUtilityV1:
    info = _level_to_float(proposal.discriminating_power)
    decision = min(1.0, info * 0.8 + (0.2 if proposal.uncertainties_targeted else 0))
    discrimination = _level_to_float(proposal.discriminating_power)
    rep = 0.7 if "representative" in proposal.objective.lower() else 0.4
    if proposal.estimated_cost_usd > 5:
        rep *= 0.5
    robust = 0.5 + (0.2 if len(proposal.hypotheses_tested) >= 2 else 0)
    return ExperimentUtilityV1(
        proposal_id=proposal.id,
        information_gain=info,
        decision_relevance=decision,
        hypothesis_discrimination=discrimination,
        expected_security_value=decision * 0.9,
        representativeness=rep,
        robustness=robust,
        compute_cost_usd=proposal.estimated_cost_usd,
        runtime_sec=proposal.estimated_runtime_sec,
        experiment_risk=_level_to_float(proposal.risk),
    )


def acquisition_score(proposal: ExperimentProposalV1, *, policy_version: str = "ghostdirector/v1") -> AcquisitionScoreV1:
    u = estimate_utility(proposal)
    cost_penalty = min(1.0, u.compute_cost_usd / 10.0)
    total = (
        u.information_gain * 1.0
        + u.decision_relevance * 1.2
        + u.representativeness * 0.6
        + u.robustness * 0.5
        - cost_penalty * 0.8
        - u.experiment_risk * 0.3
    )
    return AcquisitionScoreV1(
        proposal_id=proposal.id,
        utility=u,
        total_score=total,
        policy_version=policy_version,
        components={
            "information_gain": u.information_gain,
            "decision_value": u.decision_relevance,
            "representativeness": u.representativeness,
            "robustness": u.robustness,
            "cost_penalty": cost_penalty,
        },
    )


__all__ = ["estimate_utility", "acquisition_score"]
