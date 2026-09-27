"""Promotion readiness gates (M6/M8/fidelity/adversarial)."""

from __future__ import annotations

from dataclasses import dataclass

from ghostrange_contracts.adversarial_m8 import AdversarialVerificationReportV1, SearchStopReason
from ghostrange_contracts.ghostgate_m11 import (
    ChangeEquivalenceReportV1,
    EquivalenceStatus,
    PromotionReadinessV1,
    ReadinessDimensionStatus,
)
from ghostrange_contracts.living_twin_m6 import ClaimValidityStatus, ClaimValidityV1, TwinStalenessV1


@dataclass
class GateContext:
    claim_validities: list[ClaimValidityV1]
    twin_staleness: TwinStalenessV1 | None
    adversarial: AdversarialVerificationReportV1 | None
    fidelity_ok: bool
    equivalence: ChangeEquivalenceReportV1 | None
    rollback_tested_pass: bool
    observability_gap: bool
    high_uncertainty_blocks: bool


def evaluate_readiness(ctx: GateContext) -> PromotionReadinessV1:
    r = PromotionReadinessV1()
    blockers: list[str] = []

    if ctx.claim_validities:
        bad = [c for c in ctx.claim_validities if c.status != ClaimValidityStatus.CURRENT]
        r.claim_validity = ReadinessDimensionStatus.PASS if not bad else ReadinessDimensionStatus.FAIL
        if bad:
            blockers.append("CLAIM_NOT_CURRENT")
    else:
        r.claim_validity = ReadinessDimensionStatus.WARN

    r.fidelity = (
        ReadinessDimensionStatus.PASS if ctx.fidelity_ok else ReadinessDimensionStatus.FAIL
    )
    if not ctx.fidelity_ok:
        blockers.append("FIDELITY_INSUFFICIENT")

    if ctx.equivalence:
        if ctx.equivalence.overall == EquivalenceStatus.MATERIAL_DIFFERENCE:
            r.change_equivalence = ReadinessDimensionStatus.FAIL
            blockers.append("MATERIAL_TESTED_PRODUCTION_DIFF")
        elif ctx.equivalence.overall in (EquivalenceStatus.EXACT, EquivalenceStatus.FUNCTIONALLY_EQUIVALENT):
            r.change_equivalence = ReadinessDimensionStatus.PASS
        else:
            r.change_equivalence = ReadinessDimensionStatus.WARN
    else:
        r.change_equivalence = ReadinessDimensionStatus.SKIP

    stale = False
    if ctx.twin_staleness:
        stale = (
            ctx.twin_staleness.overall_semantic > 0.12
            or ctx.twin_staleness.config_staleness > 0.1
            or ctx.twin_staleness.identity_staleness > 0.1
        )
    if stale:
        r.source_currency = ReadinessDimensionStatus.FAIL
        blockers.append("SOURCE_DRIFT_RELEVANT")
    else:
        r.source_currency = ReadinessDimensionStatus.PASS

    if ctx.adversarial:
        if ctx.adversarial.counterexamples:
            r.adversarial_status = ReadinessDimensionStatus.FAIL
            blockers.append("COUNTEREXAMPLE_FOUND")
        elif ctx.adversarial.stop_reason == SearchStopReason.BUDGET_EXHAUSTED:
            r.adversarial_status = ReadinessDimensionStatus.WARN
        else:
            r.adversarial_status = ReadinessDimensionStatus.PASS
    else:
        r.adversarial_status = ReadinessDimensionStatus.SKIP

    r.rollback_readiness = (
        ReadinessDimensionStatus.PASS if ctx.rollback_tested_pass else ReadinessDimensionStatus.FAIL
    )
    if not ctx.rollback_tested_pass:
        blockers.append("ROLLBACK_NOT_VERIFIED")

    if ctx.observability_gap:
        r.observability_readiness = ReadinessDimensionStatus.FAIL
        blockers.append("OBSERVABILITY_GAP")
    else:
        r.observability_readiness = ReadinessDimensionStatus.PASS

    if ctx.high_uncertainty_blocks:
        r.residual_uncertainty = ReadinessDimensionStatus.FAIL
        blockers.append("HIGH_UNCERTAINTY")
    else:
        r.residual_uncertainty = ReadinessDimensionStatus.PASS

    r.blockers = blockers
    return r


def ready_for_human_review(readiness: PromotionReadinessV1) -> bool:
    if readiness.blockers:
        return False
    fails = [
        readiness.claim_validity,
        readiness.fidelity,
        readiness.change_equivalence,
        readiness.source_currency,
        readiness.adversarial_status,
        readiness.rollback_readiness,
        readiness.observability_readiness,
        readiness.residual_uncertainty,
    ]
    return all(s != ReadinessDimensionStatus.FAIL for s in fails)
