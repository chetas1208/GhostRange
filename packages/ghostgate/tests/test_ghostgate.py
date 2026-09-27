"""M11 GhostGate unit tests."""

from __future__ import annotations

import uuid

import pytest

from ghostrange_contracts.adversarial_m8 import (
    AdversarialBudgetV1,
    AdversarialClaimPhase,
    AdversarialVerificationReportV1,
    SearchPolicyId,
    SearchStopReason,
)
from ghostrange_contracts.ghostgate_m11 import (
    ChangeActionKind,
    ChangeActionV1,
    PromotionState,
)
from ghostrange_contracts.living_twin_m6 import TwinStalenessV1

from ghostrange_ghostgate.approval import create_approval_request, record_human_approval
from ghostrange_ghostgate.boundary import ProductionBoundaryGuard
from ghostrange_ghostgate.equivalence import compare_actions
from ghostrange_ghostgate.patches import auth_lab_remediation_actions
from ghostrange_ghostgate.promote import GhostGate, PromotionPrepareInput


def test_equivalence_exact_for_same_actions():
    actions = auth_lab_remediation_actions()
    report = compare_actions(actions, list(actions))
    assert report.overall.value == "EXACT"


def test_material_difference_blocks_ready():
    tested = auth_lab_remediation_actions()
    proposed = [
        ChangeActionV1(
            kind=ChangeActionKind.CONFIG,
            target_path="services/auth/other.py",
            description="Different file",
            remediation_ref="X",
        )
    ]
    report = compare_actions(tested, proposed)
    assert report.overall.value == "MATERIAL_DIFFERENCE"


def test_prepare_golden_path_ready():
    gate = GhostGate()
    exp = uuid.uuid4()
    adv = AdversarialVerificationReportV1(
        claim_id=uuid.uuid4(),
        search_run_id=uuid.uuid4(),
        phase=AdversarialClaimPhase.HARDENED_VERIFIED,
        budget=AdversarialBudgetV1(max_attempts=100),
        search_policy=SearchPolicyId.GHOSTSCHEDULER_SEARCH,
        attempts=100,
        stop_reason=SearchStopReason.BUDGET_EXHAUSTED,
    )
    res = gate.prepare(
        PromotionPrepareInput(
            experiment_id=exp,
            remediation_id=uuid.uuid4(),
            source_revision_id=uuid.uuid4(),
            twin_revision_id=uuid.uuid4(),
            evidence_root_digest="abc",
            adversarial=adv,
        )
    )
    assert res.candidate.state == PromotionState.READY_FOR_REVIEW
    assert res.candidate.change_candidate_hash
    assert "DO NOT AUTO-APPLY" in res.candidate.patch_text


def test_stale_source_requires_revalidation():
    gate = GhostGate()
    res = gate.prepare(
        PromotionPrepareInput(
            experiment_id=uuid.uuid4(),
            remediation_id=uuid.uuid4(),
            source_revision_id=uuid.uuid4(),
            twin_revision_id=uuid.uuid4(),
            evidence_root_digest="abc",
            source_stale=True,
        )
    )
    assert res.candidate.state == PromotionState.REQUIRES_REVALIDATION


def test_approval_hash_binding():
    gate = GhostGate()
    res = gate.prepare(
        PromotionPrepareInput(
            experiment_id=uuid.uuid4(),
            remediation_id=uuid.uuid4(),
            source_revision_id=uuid.uuid4(),
            twin_revision_id=uuid.uuid4(),
            evidence_root_digest="abc",
        )
    )
    cand = res.candidate
    req = create_approval_request(cand, summary="test")
    dec = record_human_approval(req, approver_id="human-1", candidate_hash=cand.change_candidate_hash)
    assert dec.decision.value == "APPROVED"
    with pytest.raises(ValueError):
        record_human_approval(req, approver_id="human-1", candidate_hash="wrong")


def test_model_cannot_approve():
    gate = GhostGate()
    res = gate.prepare(
        PromotionPrepareInput(
            experiment_id=uuid.uuid4(),
            remediation_id=uuid.uuid4(),
            source_revision_id=uuid.uuid4(),
            twin_revision_id=uuid.uuid4(),
            evidence_root_digest="abc",
        )
    )
    cand = res.candidate
    req = create_approval_request(cand, summary="test")
    with pytest.raises(PermissionError):
        record_human_approval(req, approver_id="gpt", candidate_hash=cand.change_candidate_hash, approver_kind="MODEL")


def test_forbidden_apply_in_patch_scan():
    with pytest.raises(PermissionError):
        ProductionBoundaryGuard.assert_review_only("run terraform apply -auto-approve")


def test_prepare_idempotent():
    gate = GhostGate()
    exp = uuid.uuid4()
    src = uuid.uuid4()
    twin = uuid.uuid4()
    rem = uuid.uuid4()
    base = PromotionPrepareInput(
        experiment_id=exp,
        remediation_id=rem,
        source_revision_id=src,
        twin_revision_id=twin,
        evidence_root_digest="same",
    )
    r1 = gate.prepare(base)
    r2 = gate.prepare(base)
    assert r1.candidate.id == r2.candidate.id
    assert "promotion.idempotent_replay" in r2.events
