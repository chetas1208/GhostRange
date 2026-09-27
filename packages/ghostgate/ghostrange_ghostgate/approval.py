"""Human-only approval binding to change_candidate_hash."""

from __future__ import annotations

import uuid

from ghostrange_contracts._base import utc_now
from ghostrange_contracts.ghostgate_m11 import (
    ApprovalDecisionKind,
    ApprovalDecisionV1,
    ApprovalPolicyV1,
    ApprovalRequestV1,
    ChangeRiskProfileV1,
    ProductionChangeCandidateV1,
    RiskLevel,
)

from .boundary import ProductionBoundaryGuard


def policy_for_risk(risk: ChangeRiskProfileV1) -> ApprovalPolicyV1:
    required = 1
    if risk.identity_impact == RiskLevel.HIGH or risk.data_impact == RiskLevel.HIGH:
        required = 2
    return ApprovalPolicyV1(required_approvals=required)


def create_approval_request(candidate: ProductionChangeCandidateV1, summary: str) -> ApprovalRequestV1:
    if not candidate.change_candidate_hash:
        raise ValueError("candidate hash required before approval request")
    return ApprovalRequestV1(
        change_candidate_id=candidate.id,
        change_candidate_hash=candidate.change_candidate_hash,
        summary=summary,
        required_approvals=2 if candidate.risk and candidate.risk.identity_impact == RiskLevel.HIGH else 1,
    )


def record_human_approval(
    request: ApprovalRequestV1,
    *,
    approver_id: str,
    approver_kind: str = "HUMAN",
    candidate_hash: str,
    rationale: str = "",
) -> ApprovalDecisionV1:
    ProductionBoundaryGuard.block_model_approval(approver_kind)
    if candidate_hash != request.change_candidate_hash:
        raise ValueError("Approval hash mismatch — patch or candidate changed.")
    return ApprovalDecisionV1(
        request_id=request.id,
        change_candidate_hash=candidate_hash,
        decision=ApprovalDecisionKind.APPROVED,
        approver_id=approver_id,
        approver_kind="HUMAN" if approver_kind.upper() == "HUMAN" else "SERVICE",
        rationale=rationale,
        decided_at=utc_now(),
    )


def supersede_if_hash_changed(stored_hash: str, current_hash: str) -> ApprovalDecisionKind | None:
    if stored_hash != current_hash:
        return ApprovalDecisionKind.SUPERSEDED
    return None
