"""Deterministic GhostShield policy — no LLM in verdict path."""

from __future__ import annotations

from datetime import timedelta

from ghostrange_contracts._base import utc_now
from ghostrange_contracts.ghostshield_m17 import (
    AuthorizationContextV1,
    AuthorizationVerdict,
    AuthorizationVerdictV1,
    CanonicalActionType,
    CanonicalActionV1,
)


class GhostShieldPolicyEngine:
    policy_version = "ghostshield/v1"
    policy_digest_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # v1 placeholder

    def evaluate(
        self, action: CanonicalActionV1, ctx: AuthorizationContextV1
    ) -> AuthorizationVerdictV1:
        digest = action.canonical_digest()
        reasons: list[str] = []

        if action.state_revision != ctx.runtime_revision:
            return AuthorizationVerdictV1(
                verdict=AuthorizationVerdict.STATE_STALE,
                action_digest=digest,
                reason_codes=["STATE_REVISION_MISMATCH"],
                human_explanation=(
                    f"Permit/state revision {action.state_revision} != canonical {ctx.runtime_revision}"
                ),
            )

        if ctx.safe_mode and action.action_type in (
            CanonicalActionType.CREATE_WORKER,
            CanonicalActionType.CREATE_WORLD,
            CanonicalActionType.INFERENCE_WORKER_CALL,
        ):
            return AuthorizationVerdictV1(
                verdict=AuthorizationVerdict.DENY,
                action_digest=digest,
                reason_codes=["P11_SAFE_MODE", "NO_BILLABLE_EFFECTS"],
                human_explanation="GhostRuntime SAFE_MODE blocks new billable infrastructure.",
            )

        # P2: MAX_ACTIVE_WORKERS applies to any concurrency-bounded worker effect —
        # Vultr Compute worker creation *and* Vultr Serverless Inference worker dispatch.
        if action.action_type in (
            CanonicalActionType.CREATE_WORKER,
            CanonicalActionType.INFERENCE_WORKER_CALL,
        ):
            if ctx.active_workers >= ctx.max_active_workers:
                return AuthorizationVerdictV1(
                    verdict=AuthorizationVerdict.DENY,
                    action_digest=digest,
                    reason_codes=["P2_MAX_ACTIVE_WORKERS"],
                    human_explanation=(
                        f"MAX_ACTIVE_WORKERS would be exceeded (current={ctx.active_workers}, "
                        f"max={ctx.max_active_workers})."
                    ),
                )
            plan = str(action.parameters.get("plan", ""))
            gpu = action.parameters.get("gpu_required") or "gpu" in plan.lower()
            if gpu and not ctx.allow_live_gpu:
                return AuthorizationVerdictV1(
                    verdict=AuthorizationVerdict.DENY,
                    action_digest=digest,
                    reason_codes=["P3_GPU_NOT_AUTHORIZED"],
                    human_explanation="GPU worker requires explicit live-GPU authorization.",
                )

        if action.action_type == CanonicalActionType.INFERENCE_WORKER_CALL:
            est_cost = float(action.parameters.get("estimated_cost_usd", 0.0))
            if ctx.budget_spent_usd + est_cost > ctx.budget_hard_cap_usd:
                return AuthorizationVerdictV1(
                    verdict=AuthorizationVerdict.DENY,
                    action_digest=digest,
                    reason_codes=["BUDGET_HARD_CAP", "INFERENCE_SPEND_GUARD"],
                    human_explanation=(
                        f"Inference worker spend guard: spent={ctx.budget_spent_usd:.4f} + "
                        f"est={est_cost:.4f} would exceed cap={ctx.budget_hard_cap_usd:.4f}."
                    ),
                )

        if action.action_type in (
            CanonicalActionType.TERMINATE_WORKER,
            CanonicalActionType.DESTROY_WORLD,
        ):
            if not ctx.resource_owned:
                return AuthorizationVerdictV1(
                    verdict=AuthorizationVerdict.DENY,
                    action_digest=digest,
                    reason_codes=["P1_UNOWNED_RESOURCE"],
                    human_explanation="Cannot terminate resource not owned by GhostRange campaign.",
                )

        if ctx.budget_spent_usd >= ctx.budget_hard_cap_usd and action.action_type in (
            CanonicalActionType.CREATE_WORKER,
            CanonicalActionType.START_EXPERIMENT,
            CanonicalActionType.INFERENCE_WORKER_CALL,
        ):
            return AuthorizationVerdictV1(
                verdict=AuthorizationVerdict.DENY,
                action_digest=digest,
                reason_codes=["BUDGET_HARD_CAP"],
                human_explanation="Campaign budget hard cap reached.",
            )

        if action.action_type == CanonicalActionType.ROLLBACK and not ctx.approval_digest:
            return AuthorizationVerdictV1(
                verdict=AuthorizationVerdict.REQUIRE_HUMAN,
                action_digest=digest,
                reason_codes=["P8_APPROVAL_REQUIRED"],
                human_explanation="Production rollback requires bound human approval digest.",
            )

        if action.action_type == CanonicalActionType.PROMOTE_EVOLUTION_CANDIDATE:
            if not ctx.approval_digest:
                return AuthorizationVerdictV1(
                    verdict=AuthorizationVerdict.REQUIRE_HUMAN,
                    action_digest=digest,
                    reason_codes=["M18_HUMAN_PROMOTION_REQUIRED"],
                    human_explanation="Production evolution promotion requires human approval digest.",
                )
            if not action.parameters.get("candidate_digest") or not action.parameters.get("evaluation_digest"):
                return AuthorizationVerdictV1(
                    verdict=AuthorizationVerdict.DENY,
                    action_digest=digest,
                    reason_codes=["M18_INCOMPLETE_PROMOTION_REQUEST"],
                    human_explanation="Promotion must bind exact candidate and evaluation digests.",
                )
            surface = str(action.parameters.get("learning_surface", ""))
            if surface.startswith("GHOSTSHIELD") or "INVARIANT" in surface.upper():
                return AuthorizationVerdictV1(
                    verdict=AuthorizationVerdict.DENY,
                    action_digest=digest,
                    reason_codes=["M18_HARD_POLICY_NOT_LEARNING_SURFACE"],
                    human_explanation="GhostShield hard invariants are not a learning surface.",
                )

        return AuthorizationVerdictV1(
            verdict=AuthorizationVerdict.ALLOW,
            action_digest=digest,
            reason_codes=reasons or ["POLICY_OK"],
            human_explanation="Action satisfies configured hard invariants.",
        )

    def issue_permit(self, action: CanonicalActionV1, verdict: AuthorizationVerdictV1):
        from ghostrange_contracts.ghostshield_m17 import ActionPermitV1

        if verdict.verdict != AuthorizationVerdict.ALLOW:
            raise ValueError("cannot issue permit for non-ALLOW verdict")
        exp = action.expires_at or (utc_now() + timedelta(seconds=120))
        return ActionPermitV1(
            action_digest=action.canonical_digest(),
            principal=action.principal,
            policy_version=self.policy_version,
            state_revision=action.state_revision,
            campaign_id=action.campaign_id,
            expires_at=exp,
        )
