"""Promotion gate — GhostShield + human approval; candidate cannot self-deploy."""

from __future__ import annotations

import uuid

from ghostrange_contracts.ghostevolve_m18 import (
    EvolutionCandidateV1,
    EvolutionPromotionRequestV1,
    PromotionLevel,
)
from ghostrange_contracts.ghostshield_m17 import (
    AuthorizationContextV1,
    AuthorizationVerdict,
    CanonicalActionType,
    CanonicalActionV1,
    GhostShieldMode,
)
from ghostrange_contracts.ghostarena_m19 import GhostArenaReleaseReportV1
from ghostrange_ghostarena.evolve_gate import ArenaPromotionBlocked, require_arena_for_promotion
from ghostrange_ghostshield import GhostExecutionGateway, GatewayError


class EvolutionPromotionGate:
    def __init__(self, *, mode: GhostShieldMode = GhostShieldMode.ENFORCE) -> None:
        self._gateway = GhostExecutionGateway(mode=mode)

    def authorize_promotion(
        self,
        request: EvolutionPromotionRequestV1,
        candidate: EvolutionCandidateV1,
        *,
        campaign_id: uuid.UUID | None = None,
        arena_report: GhostArenaReleaseReportV1 | None = None,
    ):
        if candidate.candidate_digest() != request.candidate_digest:
            raise GatewayError("candidate digest swap detected")
        if not (request.regression_passed and request.safety_passed and request.shadow_passed):
            raise GatewayError("evaluation gates not satisfied")
        if request.promotion_level == PromotionLevel.PRODUCTION:
            try:
                require_arena_for_promotion(arena_report)
            except ArenaPromotionBlocked as exc:
                raise GatewayError(f"GhostArena gate: {exc.report.recommendation.value}") from exc

        cid = campaign_id or uuid.UUID(int=0)
        action = CanonicalActionV1(
            action_type=CanonicalActionType.PROMOTE_EVOLUTION_CANDIDATE,
            principal="ghostevolve",
            campaign_id=cid,
            target=candidate.version_label,
            parameters={
                "candidate_digest": request.candidate_digest,
                "evaluation_digest": request.evaluation_digest,
                "rollback_target_version": request.rollback_target_version,
                "learning_surface": candidate.learning_surface.value,
            },
            state_revision=1,
            idempotency_key=request.request_digest(),
        )
        ctx = AuthorizationContextV1(
            campaign_id=cid,
            runtime_revision=1,
            active_workers=0,
            max_active_workers=99,
            budget_spent_usd=0.0,
            budget_hard_cap_usd=999.0,
            safe_mode=False,
            approval_digest=request.human_approval_digest,
        )
        verdict, permit = self._gateway.authorize(action, ctx)
        if verdict.verdict == AuthorizationVerdict.REQUIRE_HUMAN:
            return verdict, None

        def _noop():
            return {"promoted": candidate.version_label}

        result = self._gateway.execute_protected(action=action, ctx=ctx, permit=permit, effect=_noop)
        return verdict, result
