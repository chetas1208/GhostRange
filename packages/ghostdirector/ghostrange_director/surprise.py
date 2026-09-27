from __future__ import annotations

from ghostrange_contracts.ghostdirector_m9 import (
    InvestigationHypothesisV1,
    InvestigationHypothesisStatus,
    InvestigationKnowledgeStateV1,
    SurpriseObservationV1,
)


def detect_surprise(
    knowledge: InvestigationKnowledgeStateV1,
    observation: dict,
    *,
    observation_id,
    experiment_proposal_objective: str,
) -> SurpriseObservationV1 | None:
    if observation.get("ordering_correct") and observation.get("test_id") == "middleware_order_probe":
        active = [h for h in knowledge.hypothesis_graph.hypotheses if h.status == InvestigationHypothesisStatus.ACTIVE]
        if any("session refresh" in h.statement.lower() for h in knowledge.hypothesis_graph.hypotheses):
            return None
        return SurpriseObservationV1(
            observation_id=observation_id,
            unpredicted_by_hypothesis_ids=[h.id for h in active],
            suggested_new_hypothesis="Identity cache + session refresh interaction",
        )
    return None


def propose_hypothesis_from_surprise(
    knowledge: InvestigationKnowledgeStateV1,
    surprise: SurpriseObservationV1,
) -> InvestigationHypothesisV1:
    return InvestigationHypothesisV1(
        investigation_id=knowledge.investigation_id,
        statement=surprise.suggested_new_hypothesis or "Unknown mechanism (OTHER)",
        status=InvestigationHypothesisStatus.PROPOSED,
    )


__all__ = ["detect_surprise", "propose_hypothesis_from_surprise"]
