"""GhostDirector + inference-assisted proposals (model never owns policy)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request
from ghostrange_contracts.ghostdirector_m9 import (
    DirectorPolicyId,
    ExperimentCampaignBudgetV1,
    InvestigationKnowledgeStateV1,
)
from pydantic import BaseModel, Field

from ghostrange_director.director import GhostDirectorSimulator
from ghostrange_director.scenarios.auth_incident import build_auth_incident_knowledge

from .inference_service import InferenceService

router = APIRouter(prefix="/v1/director", tags=["director"])


class AnalyzeRequest(BaseModel):
    incident_summary: str = Field(..., min_length=8, max_length=4000)
    range_id: str | None = None


@router.post("/campaign/simulate")
async def simulate_campaign():
    """Deterministic GhostDirector path (no inference spend)."""
    knowledge = build_auth_incident_knowledge()
    sim = GhostDirectorSimulator()
    campaign = sim.run_campaign(
        knowledge,
        policy=DirectorPolicyId.GHOSTDIRECTOR_V1,
        budget=ExperimentCampaignBudgetV1(max_experiments=8, max_compute_usd=10.0),
        max_rounds=3,
    )
    return {
        "campaign_id": str(campaign.id),
        "state": campaign.state.value,
        "experiments_run": len(campaign.observations),
        "stop_reason": campaign.stop_reason.value if campaign.stop_reason else None,
        "path": "deterministic_simulator",
    }


@router.post("/analyze")
async def analyze_with_inference(request: Request, body: AnalyzeRequest):
    """Frontend → API → inference → validated structured proposal (policy stays server-side)."""
    settings = request.app.state.settings
    inference = InferenceService(settings)
    if not inference.available:
        raise HTTPException(503, "inference not configured")

    system = (
        "You are GhostDirector assistant. Return ONLY valid JSON with keys: "
        "hypothesis (string), experiment_proposal (string), explanation (string), "
        "confidence (number 0-1). Do not include resource IDs or authorization decisions."
    )
    structured: dict
    inference_degraded = False
    try:
        structured = await inference.complete_json(system=system, user=body.incident_summary)
        for key in ("hypothesis", "experiment_proposal", "explanation", "confidence"):
            if key not in structured:
                raise ValueError(f"missing {key}")
        confidence = float(structured["confidence"])
        if confidence < 0 or confidence > 1:
            raise ValueError("confidence out of range")
    except Exception:
        inference_degraded = True
        structured = {
            "hypothesis": "Session or cache invalidation race in auth middleware",
            "experiment_proposal": "Replay login flow with forced session rotation under load",
            "explanation": "Deterministic fallback — inference response was not valid JSON",
            "confidence": 0.35,
        }

    # Deterministic director still authoritative for scheduling decisions.
    knowledge: InvestigationKnowledgeStateV1 = build_auth_incident_knowledge()
    sim = GhostDirectorSimulator()
    campaign = sim.run_campaign(
        knowledge,
        budget=ExperimentCampaignBudgetV1(max_experiments=4, max_compute_usd=5.0),
        max_rounds=1,
    )

    rid = body.range_id or str(uuid.uuid4())
    return {
        "range_id": rid,
        "model_proposal": structured,
        "director_campaign_id": str(campaign.id),
        "director_state": campaign.state.value,
        "policy_note": "Scheduler/world/cost limits enforced server-side; model output is advisory only",
        "inference_degraded": inference_degraded,
    }
