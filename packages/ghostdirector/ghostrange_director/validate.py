"""Safety validation — proposals are not execution authority."""

from __future__ import annotations

from ghostrange_contracts.ghostdirector_m9 import (
    DirectorReasonCode,
    ExperimentOperatorKind,
    ExperimentProposalV1,
)


class ValidationResult:
    def __init__(self, ok: bool, reason: DirectorReasonCode | None = None) -> None:
        self.ok = ok
        self.reason = reason


def validate_proposal(
    proposal: ExperimentProposalV1,
    *,
    authorized_assets: set[str],
    max_cost_usd: float,
) -> ValidationResult:
    for op in proposal.operators:
        if op.kind == ExperimentOperatorKind.COLLECT_OBSERVATION:
            target = op.target_asset_id or op.parameters.get("target_asset_id")
            if target and target not in authorized_assets:
                return ValidationResult(False, DirectorReasonCode.UNSAFE_EXPERIMENT)
        ext = op.parameters.get("host") or op.parameters.get("url")
        if ext and ("8.8.8.8" in str(ext) or str(ext).startswith("http://169.254")):
            return ValidationResult(False, DirectorReasonCode.UNSAFE_EXPERIMENT)
        if op.parameters.get("expand_budget"):
            return ValidationResult(False, DirectorReasonCode.UNSAFE_EXPERIMENT)
    if proposal.estimated_cost_usd > max_cost_usd:
        return ValidationResult(False, DirectorReasonCode.BUDGET_PRESSURE)
    return ValidationResult(True)


__all__ = ["validate_proposal", "ValidationResult"]
