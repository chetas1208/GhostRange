"""Rule-based experiment candidates — not LLM-dependent."""

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


def generate_candidates(knowledge: InvestigationKnowledgeStateV1) -> list[ExperimentProposalV1]:
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
        proposals.append(
            ExperimentProposalV1(
                investigation_id=inv,
                objective=f"Discriminate {h1.statement[:40]} vs {h2.statement[:40]}",
                hypotheses_tested=[h1.id, h2.id],
                uncertainties_targeted=[u.id for u in knowledge.uncertainties[:1]],
                operators=[
                    ExperimentOperatorV1(
                        kind=ExperimentOperatorKind.COLLECT_OBSERVATION,
                        parameters={"test_id": "middleware_order_probe"},
                        target_asset_id="asset/gw01",
                    )
                ],
                expected_outcomes=[
                    ExpectedOutcomeV1(if_hypothesis_id=h1.id, observation_key="middleware_first", expected_value=True),
                    ExpectedOutcomeV1(if_hypothesis_id=h2.id, observation_key="middleware_first", expected_value=False),
                ],
                discriminating_power=BeliefLevel.HIGH,
                estimated_cost_usd=0.5,
                estimated_runtime_sec=30,
                origin=CandidateOrigin.RULE,
            )
        )

    for h in active:
        proposals.append(
            ExperimentProposalV1(
                investigation_id=inv,
                objective=f"Gateway routing probe for hypothesis {str(h.id)[:8]}",
                hypotheses_tested=[h.id],
                operators=[
                    ExperimentOperatorV1(
                        kind=ExperimentOperatorKind.COLLECT_OBSERVATION,
                        parameters={"test_id": "gateway_route_probe"},
                        target_asset_id="asset/gw01",
                    )
                ],
                discriminating_power=BeliefLevel.MEDIUM,
                estimated_cost_usd=1.0,
                estimated_runtime_sec=60,
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

    if any("session refresh" in h.statement.lower() for h in hyps):
        proposals.append(
            ExperimentProposalV1(
                investigation_id=inv,
                objective="Session refresh + cache interaction probe",
                hypotheses_tested=[h.id for h in hyps if "session refresh" in h.statement.lower()],
                operators=[
                    ExperimentOperatorV1(
                        kind=ExperimentOperatorKind.CHANGE_SYNTHETIC_IDENTITY_STATE,
                        parameters={"test_id": "session_refresh_probe"},
                        target_asset_id="asset/gw01",
                    )
                ],
                discriminating_power=BeliefLevel.HIGH,
                estimated_cost_usd=0.8,
                estimated_runtime_sec=45,
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
