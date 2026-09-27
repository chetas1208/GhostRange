"""M12 GhostWatch API — observe simulated/controlled rollouts only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ghostrange_contracts.ghostwatch_m12 import DeploymentAuthorityMode

from ghostrange_contracts.ghostwatch_m12 import ExternalDeploymentRecordV1, ObservedDeploymentStateV1

from ghostrange_ghostwatch.campaign import GhostWatch, StartCampaignInput
from ghostrange_ghostwatch.ingest import apply_external_record, verify_external_record
from ghostrange_ghostwatch.ledger_bridge import InMemoryPromotionLedger
from ghostrange_ghostwatch.policy import load_policy
from ghostrange_ghostwatch.director_bridge import propose_from_surprise
from ghostrange_ghostwatch.simulator import ProductionRolloutSimulator, SimScenario

from .ghostgate_service import gate as ghostgate
from .config import Settings

router = APIRouter(prefix="/v1/ghostwatch", tags=["ghostwatch"])
_watch = GhostWatch()
_ledger = InMemoryPromotionLedger()


def _policy():
    s = Settings.from_env()
    return load_policy(s.repo_root / "config/ghostwatch-policy.yaml")


class SimulateBody(BaseModel):
    scenario: str = Field(default="good-canary")
    authority_mode: DeploymentAuthorityMode = DeploymentAuthorityMode.RECOMMEND


@router.post("/simulate")
async def simulate_rollout(body: SimulateBody):
    """SIMULATED_ROLLOUT — not production."""
    try:
        scenario = SimScenario(body.scenario)
    except ValueError as exc:
        raise HTTPException(400, f"unknown scenario: {body.scenario}") from exc
    results = ProductionRolloutSimulator().run_scenario(scenario, authority=body.authority_mode)
    return {
        "label": "SIMULATED_ROLLOUT",
        "scenario": scenario.value,
        "steps": [
            {
                "stage": r.stage.value,
                "campaign_state": r.campaign_state.value,
                "analysis_outcome": r.analysis_outcome,
                "events": r.events,
            }
            for r in results
        ],
    }


class StartCampaignBody(BaseModel):
    candidate_id: str
    approver_id: str
    approved_artifact_digest: str = "sha256:auth-v2.7"
    rollback_target_digest: str = "sha256:auth-v2.6"
    authority_mode: DeploymentAuthorityMode = DeploymentAuthorityMode.OBSERVE_ONLY


@router.post("/campaigns/start")
async def start_campaign(body: StartCampaignBody):
    """Start observing an external deployment bound to approved candidate."""
    try:
        cid = uuid.UUID(body.candidate_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid candidate_id") from exc
    cand = ghostgate.get(cid)
    if not cand:
        raise HTTPException(404, "candidate not found")
    from ghostrange_ghostwatch.adapters.mock import MockDeploymentExecutorAdapter
    from ghostrange_ghostgate.approval import create_approval_request, record_human_approval

    if cand.state.value not in ("READY_FOR_REVIEW", "APPROVED"):
        raise HTTPException(409, f"candidate not approvable: {cand.state.value}")
    req = create_approval_request(cand, summary="GhostWatch campaign bind")
    try:
        dec = record_human_approval(
            req,
            approver_id=body.approver_id,
            candidate_hash=cand.change_candidate_hash,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc

    adapter = MockDeploymentExecutorAdapter(
        approved_digest=body.approved_artifact_digest,
        rollback_digest=body.rollback_target_digest,
    )
    camp = _watch.start_campaign(
        StartCampaignInput(
            candidate=cand,
            approval=dec,
            approved_artifact_digest=body.approved_artifact_digest,
            rollback_target_digest=body.rollback_target_digest,
            authority_mode=body.authority_mode,
            adapter=adapter,
        )
    )
    _ledger.append(
        "ghostwatch.campaign_started",
        {
            "campaign_id": str(camp.id),
            "approved_change_hash": cand.change_candidate_hash,
            "authority_mode": body.authority_mode.value,
        },
    )
    return {
        "campaign_id": str(camp.id),
        "state": camp.state.value,
        "authority_mode": camp.execution.authority_mode.value,
        "environment": camp.execution.environment_reference,
        "message": "OBSERVATION ONLY unless authority_mode permits scoped control",
    }


class ExternalRecordBody(BaseModel):
    executor: str
    external_id: str
    event_id: str = ""
    sequence: int = 0
    approved_change_hash: str = ""
    artifact_digest: str
    service_version: str = ""
    traffic_percentage_new: float = 0


@router.post("/campaigns/{campaign_id}/external-record")
async def ingest_external_record(campaign_id: str, body: ExternalRecordBody):
    """Ingress hook (M11 ExternalDeploymentRecordV1) — authenticated status from executor."""
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid campaign_id") from exc
    camp = _watch.get(cid)
    if not camp:
        raise HTTPException(404, "not found")
    record = ExternalDeploymentRecordV1(
        executor=body.executor,
        external_id=body.external_id,
        campaign_id=cid,
        approved_change_hash=body.approved_change_hash or camp.execution.approved_change_hash,
        event_id=body.event_id or body.external_id,
        sequence=body.sequence,
        observed_state=ObservedDeploymentStateV1(
            artifact_digest=body.artifact_digest,
            service_version=body.service_version,
            traffic_percentage_new=body.traffic_percentage_new,
            source=body.executor,
        ),
    )
    try:
        tick = _watch.ingest_external(cid, record)
    except Exception as exc:
        raise HTTPException(409, str(exc)) from exc
    for ev in tick.events:
        _ledger.append(ev, {"campaign_id": campaign_id})
    return {"state": tick.state.value, "events": tick.events}


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid campaign_id") from exc
    camp = _watch.get(cid)
    if not camp:
        raise HTTPException(404, "not found")
    surprises = _watch.surprises(cid)
    proposals = [propose_from_surprise(s).__dict__ for s in surprises]
    return {
        "campaign": camp.model_dump(mode="json"),
        "surprises": [s.model_dump(mode="json") for s in surprises],
        "director_proposals": proposals,
    }
