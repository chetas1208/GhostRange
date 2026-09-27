"""Campaign recovery orchestration (deterministic policy core)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ghostrange_contracts.ghostruntime_m16 import (
    CampaignRuntimeState,
    RecoveryAction,
    RecoveryDecisionV1,
    SideEffectStatus,
)


@dataclass
class RecoveryContext:
    campaign_id: Any
    lifecycle: CampaignRuntimeState
    unknown_effects: list[str] = field(default_factory=list)
    provider_workers_observed: list[str] = field(default_factory=list)
    provider_workers_expected: list[str] = field(default_factory=list)
    budget_spent_usd: float = 0.0
    budget_hard_cap_usd: float = 0.0
    canonical_results_present: set[str] = field(default_factory=set)


class CampaignRecoveryManager:
    """Deterministic recovery decisions — no LLM authority."""

    def decide(self, ctx: RecoveryContext) -> RecoveryDecisionV1:
        if ctx.budget_spent_usd >= ctx.budget_hard_cap_usd:
            return RecoveryDecisionV1(
                campaign_id=ctx.campaign_id,
                action=RecoveryAction.SAFE_MODE,
                reason_codes=["BUDGET_EXHAUSTED"],
            )
        if ctx.unknown_effects:
            if ctx.provider_workers_observed:
                return RecoveryDecisionV1(
                    campaign_id=ctx.campaign_id,
                    action=RecoveryAction.RESUME,
                    reason_codes=["PROVIDER_EFFECT_FOUND", "ADOPT_EXISTING_WORKER"],
                )
            return RecoveryDecisionV1(
                campaign_id=ctx.campaign_id,
                action=RecoveryAction.SAFE_MODE,
                reason_codes=["PROVIDER_EFFECT_UNKNOWN", "RECONCILE_BEFORE_MUTATE"],
            )
        return RecoveryDecisionV1(
            campaign_id=ctx.campaign_id,
            action=RecoveryAction.RESUME,
            reason_codes=["CHECKPOINT_VALID", "STATE_CONSISTENT"],
        )

    def reconcile_unknown_create(
        self, *, observed_provider_id: str | None
    ) -> tuple[SideEffectStatus, list[str]]:
        if observed_provider_id:
            return SideEffectStatus.COMPLETED, ["PROVIDER_EFFECT_FOUND", "ADOPT_EXISTING_WORKER"]
        return SideEffectStatus.FAILED, ["PROVIDER_EFFECT_ABSENT"]
