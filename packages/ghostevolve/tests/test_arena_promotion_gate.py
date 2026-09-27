import uuid

import pytest

from ghostrange_contracts.ghostarena_m19 import ReleaseRecommendation
from ghostrange_contracts.ghostevolve_m18 import EvolutionPromotionRequestV1, LearningSurface, EvolutionCandidateV1
from ghostrange_contracts.ghostshield_m17 import GhostShieldMode
from ghostrange_ghostarena.engine import GhostArenaEngine
from ghostrange_ghostevolve.promotion import EvolutionPromotionGate
from ghostrange_ghostshield import GatewayError


def _req_and_cand():
    cand = EvolutionCandidateV1(
        learning_surface=LearningSurface.STOPPING_POLICY,
        version_label="stopping-policy:v6",
        champion_version="stopping-policy:v5",
    )
    req = EvolutionPromotionRequestV1(
        candidate_digest=cand.candidate_digest(),
        baseline_digest="b",
        evaluation_digest="e",
        regression_passed=True,
        safety_passed=True,
        shadow_passed=True,
        rollback_target_version="stopping-policy:v5",
        human_approval_digest="human:ok",
        arena_qualified=False,
    )
    return req, cand


def test_production_promotion_blocked_without_arena_report():
    gate = EvolutionPromotionGate(mode=GhostShieldMode.ENFORCE)
    req, cand = _req_and_cand()
    with pytest.raises(GatewayError, match="GhostArena"):
        gate.authorize_promotion(req, cand, campaign_id=uuid.uuid4(), arena_report=None)


def test_production_promotion_blocked_when_not_qualified():
    gate = EvolutionPromotionGate(mode=GhostShieldMode.ENFORCE)
    req, cand = _req_and_cand()
    engine = GhostArenaEngine()
    report = engine.release_report(
        baseline_version="stopping-policy:v5",
        candidate_version="stopping-policy:v6",
        candidate_policy="fast_premature",
    )
    assert report.recommendation == ReleaseRecommendation.NOT_QUALIFIED
    with pytest.raises(GatewayError, match="NOT_QUALIFIED"):
        gate.authorize_promotion(req, cand, campaign_id=uuid.uuid4(), arena_report=report)
