"""Rule-based experiment candidates — not LLM-dependent.

The discriminator probe, the per-hypothesis probe and the "hidden mechanism" probe are all
scenario content, supplied via a :class:`~ghostrange_director.mechanics.ScenarioMechanics`
(defaults to the original auth-incident scenario so existing callers are unaffected). Only the
generic decoy experiment (expensive, unrepresentative, budget-wasting — used to exercise the
acquisition scorer's cost penalty regardless of which incident is loaded) and the
counterexample-search proposal stay scenario-agnostic here.
"""

from __future__ import annotations

from uuid import uuid4

from ghostrange_contracts.ghostdirector_m9 import (
    BeliefLevel,
    CandidateOrigin,
    ExperimentOperatorKind,
    ExperimentOperatorV1,
    ExperimentProposalV1,
    ExpectedOutcomeV1,
    InvestigationHypothesisStatus,
    InvestigationKnowledgeStateV1,
)

from .mechanics import ScenarioMechanics, default_mechanics


def generate_candidates(
    knowledge: InvestigationKnowledgeStateV1,
    *,
    mechanics: ScenarioMechanics | None = None,
) -> list[ExperimentProposalV1]:
    mechanics = mechanics or default_mechanics()
    inv = knowledge.investigation_id
    hyps = knowledge.hypothesis_graph.hypotheses
    active = [
        h
        for h in hyps
        if h.status
        in (
            InvestigationHypothesisStatus.ACTIVE,
            InvestigationHypothesisStatus.PROPOSED,
            InvestigationHypothesisStatus.UNRESOLVED,
        )
    ]
    proposals: list[ExperimentProposalV1] = []

    if len(active) >= 2:
        h1, h2 = active[0], active[1]
        dp = mechanics.discriminate_probe
        proposals.append(
            ExperimentProposalV1(
                investigation_id=inv,
                objective=dp.objective.format(h1=h1.statement[:40], h2=h2.statement[:40]),
                hypotheses_tested=[h1.id, h2.id],
                uncertainties_targeted=[u.id for u in knowledge.uncertainties[:1]],
                operators=[
                    ExperimentOperatorV1(
                        kind=dp.operator_kind,
                        parameters={"test_id": dp.test_id},
                        target_asset_id=dp.target_asset_id,
                    )
                ],
                expected_outcomes=[
                    ExpectedOutcomeV1(
                        if_hypothesis_id=h1.id, observation_key=dp.discriminate_observation_key, expected_value=True
                    ),
                    ExpectedOutcomeV1(
                        if_hypothesis_id=h2.id, observation_key=dp.discriminate_observation_key, expected_value=False
                    ),
                ],
                discriminating_power=dp.discriminating_power,
                estimated_cost_usd=dp.cost_usd,
                estimated_runtime_sec=dp.runtime_sec,
                origin=CandidateOrigin.RULE,
            )
        )

    for h in active:
        php = mechanics.per_hypothesis_probe
        proposals.append(
            ExperimentProposalV1(
                investigation_id=inv,
                objective=php.objective.format(hid=str(h.id)[:8]),
                hypotheses_tested=[h.id],
                operators=[
                    ExperimentOperatorV1(
                        kind=php.operator_kind,
                        parameters={"test_id": php.test_id},
                        target_asset_id=php.target_asset_id,
                    )
                ],
                discriminating_power=php.discriminating_power,
                estimated_cost_usd=php.cost_usd,
                estimated_runtime_sec=php.runtime_sec,
                origin=CandidateOrigin.RULE,
            )
        )

    proposals.append(
        ExperimentProposalV1(
            investigation_id=inv,
            objective="Expensive redundant full traffic capture (unrepresentative)",
            hypotheses_tested=[h.id for h in active[:1]],
            operators=[
                ExperimentOperatorV1(
                    kind=ExperimentOperatorKind.COLLECT_OBSERVATION,
                    parameters={"test_id": "full_pcap_redundant"},
                    target_asset_id="asset/gw01",
                )
            ],
            discriminating_power=BeliefLevel.HIGH,
            estimated_cost_usd=8.0,
            estimated_runtime_sec=600,
            origin=CandidateOrigin.RULE,
        )
    )

    hp = mechanics.hidden_probe
    if hp and any(hp.matches(h) for h in hyps):
        proposals.append(
            ExperimentProposalV1(
                investigation_id=inv,
                objective=hp.objective,
                hypotheses_tested=[h.id for h in hyps if hp.matches(h)],
                operators=[
                    ExperimentOperatorV1(
                        kind=hp.operator_kind,
                        parameters={"test_id": hp.test_id},
                        target_asset_id=hp.target_asset_id,
                    )
                ],
                discriminating_power=hp.discriminating_power,
                estimated_cost_usd=hp.cost_usd,
                estimated_runtime_sec=hp.runtime_sec,
                origin=CandidateOrigin.RULE,
            )
        )

    if knowledge.counterexample_ids:
        proposals.append(
            ExperimentProposalV1(
                investigation_id=inv,
                objective="Run bounded counterexample search",
                hypotheses_tested=[h.id for h in active],
                operators=[
                    ExperimentOperatorV1(
                        kind=ExperimentOperatorKind.RUN_COUNTEREXAMPLE_SEARCH,
                        parameters={"budget_attempts": 50},
                        target_asset_id="asset/gw01",
                    )
                ],
                discriminating_power=BeliefLevel.MEDIUM,
                estimated_cost_usd=3.0,
                estimated_runtime_sec=120,
                origin=CandidateOrigin.COUNTEREXAMPLE,
            )
        )

    return proposals


__all__ = ["generate_candidates"]
