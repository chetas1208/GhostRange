import uuid

import pytest

from ghostrange_contracts.ghostevolve_m18 import (
    EvolutionCandidateState,
    EvolutionCandidateV1,
    EvolutionPromotionRequestV1,
    LearningSurface,
)
from ghostrange_contracts.ghostshield_m17 import AuthorizationVerdict, GhostShieldMode
from ghostrange_ghostarena.engine import GhostArenaEngine
from ghostrange_ghostevolve.promotion import EvolutionPromotionGate


def _qualified_arena_report():
    return GhostArenaEngine().release_report(
        baseline_version="runtime-estimator:v6",
        candidate_version="runtime-estimator:v7",
        candidate_policy="qualified",
    )


def _candidate() -> EvolutionCandidateV1:
    c = EvolutionCandidateV1(
        learning_surface=LearningSurface.SCHEDULER_RUNTIME_ESTIMATOR,
        version_label="runtime-estimator:v5",
        champion_version="runtime-estimator:v4-m15",
        artifact_digest="abc",
        training_manifest_digest="def",
        state=EvolutionCandidateState.CANARY,
    )
    return c


def test_promotion_requires_human_approval():
    gate = EvolutionPromotionGate(mode=GhostShieldMode.ENFORCE)
    cand = _candidate()
    req = EvolutionPromotionRequestV1(
        candidate_digest=cand.candidate_digest(),
        baseline_digest="baseline",
        evaluation_digest="eval",
        regression_passed=True,
        safety_passed=True,
        shadow_passed=True,
        rollback_target_version="runtime-estimator:v4-m15",
        human_approval_digest=None,
    )
    verdict, _ = gate.authorize_promotion(req, cand, arena_report=_qualified_arena_report())
    assert verdict.verdict == AuthorizationVerdict.REQUIRE_HUMAN


def test_promotion_with_approval_and_exact_digest():
    gate = EvolutionPromotionGate(mode=GhostShieldMode.ENFORCE)
    cand = _candidate()
    req = EvolutionPromotionRequestV1(
        candidate_digest=cand.candidate_digest(),
        baseline_digest="baseline",
        evaluation_digest="eval",
        regression_passed=True,
        safety_passed=True,
        shadow_passed=True,
        rollback_target_version="runtime-estimator:v4-m15",
        human_approval_digest="human:approved:v5",
    )
    verdict, result = gate.authorize_promotion(
        req, cand, campaign_id=uuid.uuid4(), arena_report=_qualified_arena_report()
    )
    assert verdict.verdict == AuthorizationVerdict.ALLOW
    assert result is not None
    assert result.enforced


def test_candidate_digest_swap_blocked():
    gate = EvolutionPromotionGate(mode=GhostShieldMode.ENFORCE)
    cand = _candidate()
    req = EvolutionPromotionRequestV1(
        candidate_digest="wrong-digest",
        baseline_digest="baseline",
        evaluation_digest="eval",
        regression_passed=True,
        safety_passed=True,
        shadow_passed=True,
        rollback_target_version="runtime-estimator:v4-m15",
        human_approval_digest="human:approved",
    )
    from ghostrange_ghostshield import GatewayError

    with pytest.raises(GatewayError, match="digest swap"):
        gate.authorize_promotion(req, cand)
