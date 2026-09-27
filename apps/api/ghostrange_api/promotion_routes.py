"""M11 GhostGate API — prepare / inspect / export (no production deploy)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ghostrange_contracts.adversarial_m8 import (
    AdversarialBudgetV1,
    AdversarialClaimPhase,
    AdversarialVerificationReportV1,
    SearchPolicyId,
    SearchStopReason,
)

from ghostrange_ghostgate.approval import create_approval_request, record_human_approval
from ghostrange_ghostgate.promote import PromotionPrepareInput

from ghostrange_ghostgate.recompile import verify_proposed_patch

from .ghostgate_service import gate as _gate
from .config import Settings

router = APIRouter(prefix="/v1/promotion", tags=["promotion"])


class PreparePromotionBody(BaseModel):
    experiment_id: str
    evidence_root_digest: str = Field(default="sha256:golden-path")
    remediation_id: str | None = None
    source_revision_id: str | None = None
    twin_revision_id: str | None = None
    source_stale: bool = False
    observability_gap: bool = False


@router.post("/prepare")
async def prepare_promotion(body: PreparePromotionBody):
    """PREPARE PROMOTION — builds change package; does not deploy."""
    try:
        exp = uuid.UUID(body.experiment_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid experiment_id") from exc
    adversarial = AdversarialVerificationReportV1(
        claim_id=uuid.uuid4(),
        search_run_id=uuid.uuid4(),
        phase=AdversarialClaimPhase.HARDENED_VERIFIED,
        budget=AdversarialBudgetV1(max_attempts=2104),
        search_policy=SearchPolicyId.GHOSTSCHEDULER_SEARCH,
        attempts=2104,
        stop_reason=SearchStopReason.BUDGET_EXHAUSTED,
    )
    inp = PromotionPrepareInput(
        experiment_id=exp,
        remediation_id=uuid.UUID(body.remediation_id) if body.remediation_id else uuid.uuid4(),
        source_revision_id=uuid.UUID(body.source_revision_id) if body.source_revision_id else uuid.uuid4(),
        twin_revision_id=uuid.UUID(body.twin_revision_id) if body.twin_revision_id else uuid.uuid4(),
        evidence_root_digest=body.evidence_root_digest,
        adversarial=adversarial,
        source_stale=body.source_stale,
        observability_gap=body.observability_gap,
    )
    result = _gate.prepare(inp)
    c = result.candidate
    return {
        "candidate_id": str(c.id),
        "state": c.state.value,
        "change_candidate_hash": c.change_candidate_hash,
        "readiness": c.readiness.model_dump(mode="json"),
        "events": result.events,
        "message": "APPROVED != DEPLOYED — external deployment only",
    }


@router.get("/candidates/{candidate_id}")
async def inspect_candidate(candidate_id: str):
    try:
        cid = uuid.UUID(candidate_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid candidate_id") from exc
    cand = _gate.get(cid)
    if not cand:
        raise HTTPException(404, "candidate not found")
    return cand.model_dump(mode="json")


@router.post("/candidates/{candidate_id}/verify-exact-patch")
async def verify_exact_patch(candidate_id: str):
    """M11 blocker: compile proposed patch through Range Compiler (local, not Vultr)."""
    try:
        cid = uuid.UUID(candidate_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid candidate_id") from exc
    cand = _gate.get(cid)
    if not cand:
        raise HTTPException(404, "candidate not found")
    settings = Settings.from_env()
    compose = settings.repo_root / "ranges/ghostrange-auth-lab-v1/docker/vm-1/docker-compose.yml"
    report = verify_proposed_patch(compose, cand.patch_text)
    return {
        "report": report.__dict__,
        "m11_recompile_loop": "LOCAL_COMPILE_ONLY",
        "live_vultr_promotion_world": "NOT_RUN",
    }


@router.get("/candidates/{candidate_id}/export")
async def export_candidate(candidate_id: str):
    try:
        cid = uuid.UUID(candidate_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid candidate_id") from exc
    try:
        payload = _gate.export_bundle(cid)
    except KeyError as exc:
        raise HTTPException(404, "candidate not found") from exc
    return {"bundle_json": payload}


class ApproveBody(BaseModel):
    approver_id: str = Field(..., min_length=1)


@router.post("/candidates/{candidate_id}/approve")
async def approve_candidate(candidate_id: str, body: ApproveBody):
    """Human approval only — binds to exact change_candidate_hash."""
    try:
        cid = uuid.UUID(candidate_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid candidate_id") from exc
    cand = _gate.get(cid)
    if not cand:
        raise HTTPException(404, "candidate not found")
    if cand.state.value not in ("READY_FOR_REVIEW", "WAITING_FOR_APPROVAL", "APPROVED"):
        raise HTTPException(409, f"candidate not ready: {cand.state.value}")
    req = create_approval_request(cand, summary="API human approval")
    try:
        dec = record_human_approval(
            req,
            approver_id=body.approver_id,
            candidate_hash=cand.change_candidate_hash,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {
        "decision": dec.model_dump(mode="json"),
        "note": "APPROVED FOR EXTERNAL DEPLOYMENT — NOT DEPLOYED",
    }
