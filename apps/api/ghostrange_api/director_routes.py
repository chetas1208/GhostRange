"""GhostDirector + inference-assisted proposals (model never owns policy)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from ghostrange_contracts.ghostdirector_m9 import (
    DirectorPolicyId,
    ExperimentCampaignBudgetV1,
    InvestigationKnowledgeStateV1,
)
from pydantic import BaseModel, Field

from ghostrange_director.director import GhostDirectorSimulator
from ghostrange_director.scenarios.auth_incident import build_auth_incident_knowledge

router = APIRouter(prefix="/v1/director", tags=["director"])

# The only 4 fields a free-text model proposal is ever allowed to carry past this route.
# Treat the model's output as an untrusted structured proposal: whatever else it emits (an
# attempted "action", "approved", "cost_usd", resource id, etc. — real, malformed-by-mistake,
# or actively adversarial) is dropped here and never reaches the response, the deterministic
# GhostDirectorSimulator campaign below, or (a fortiori) GhostExecutionGateway. See
# apps/api/tests/test_laya_ghostshield_bypass_proof.py.
_ALLOWED_PROPOSAL_KEYS = ("hypothesis", "experiment_proposal", "explanation", "confidence")

# Fixed, typed classification questions for the DEFAULT-ON `InferenceRouter.classify()` call
# below (see inference_router.py — Laya-first by default, no INTELLIGENCE_PROVIDER opt-in
# required). Deliberately small and fixed: this is exactly the "structured
# classification/extraction" use case the real Laya model genuinely supports, and it is
# never used to decide anything — see `_ALLOWED_CLASSIFICATION_SEVERITIES` /
# `classification` in the response, which is advisory only, same as `model_proposal`.
_CLASSIFICATION_QUESTIONS = {
    "severity": {
        "type": "choice",
        "instructions": "How severe is this incident, based only on the state described?",
        "criteria": {
            "low": "minor, no meaningful user impact",
            "medium": "partial degradation or a bounded subset of users affected",
            "high": "major user-facing outage or broad degradation",
            "critical": "total outage, data loss/exposure risk, or a security breach",
        },
    },
    "needs_immediate_action": {
        "type": "noul",
        "instructions": (
            "Does this incident likely require immediate remediation (e.g. a rollback) "
            "rather than further investigation first?"
        ),
    },
}
_ALLOWED_CLASSIFICATION_SEVERITIES = frozenset({"low", "medium", "high", "critical"})


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
    """Frontend → API → InferenceRouter → validated, sanitized structured proposal (policy
    stays server-side).

    Two independent, separately-degrading model-assisted steps, both advisory-only:

    1. Free-text proposal (`model_proposal`) — hypothesis/experiment_proposal/explanation
       prose. Always served by the existing Vultr provider in practice: real Laya cannot
       generate free text at all, so even with INTELLIGENCE_PROVIDER=laya-local set, the
       router's own fallback resolves this to the existing provider every time (see
       inference_providers.py's module docstring). Falls back further to a canned,
       deterministic proposal (`inference_degraded=True`) if no provider is configured or
       the call fails.

    2. Structured classification (`classification`) — a small, fixed severity/urgency
       read on the incident text via `InferenceRouter.classify()`. This is DEFAULT-ON: it
       tries the real local Laya model FIRST whenever one is reachable (no
       INTELLIGENCE_PROVIDER opt-in needed — MODEL_BASE_URL/MODEL_API_PROTOCOL already
       default to exactly that), falls back to the existing provider's own
       LLM-prompted classification if Laya is unreachable, and is simply omitted
       (`classification: null`) if neither is configured or the result doesn't validate.

    Neither step's output ever influences the deterministic `GhostDirectorSimulator`
    campaign run below, and neither this route nor anything it calls ever constructs a
    GhostExecutionGateway action from either — see
    apps/api/tests/test_laya_ghostshield_bypass_proof.py for the proof.
    """
    inference_router = request.app.state.inference_router

    # --- Step 1: free-text proposal (existing behavior, provider-agnostic to the caller) ---
    structured: dict
    inference_degraded = False
    served_by = "deterministic_fallback"
    if inference_router.available:
        system = (
            "You are GhostDirector assistant. Return ONLY valid JSON with keys: "
            "hypothesis (string), experiment_proposal (string), explanation (string), "
            "confidence (number 0-1). Do not include resource IDs or authorization decisions."
        )
        try:
            routed = await inference_router.structured_generate(system=system, user=body.incident_summary)
            raw = routed.data
            for key in _ALLOWED_PROPOSAL_KEYS:
                if key not in raw:
                    raise ValueError(f"missing {key}")
            confidence = float(raw["confidence"])
            if confidence < 0 or confidence > 1:
                raise ValueError("confidence out of range")
            # Sanitize before anything downstream (including this response) sees it: only
            # _ALLOWED_PROPOSAL_KEYS survive, coerced to their expected types. A model
            # response that also included e.g. {"action": "CREATE_WORKER", "approved": true}
            # has those extra fields dropped right here, not merely "ignored later".
            structured = {key: str(raw[key]) for key in _ALLOWED_PROPOSAL_KEYS if key != "confidence"}
            structured["confidence"] = confidence
            inference_degraded = routed.degraded
            served_by = routed.provider
        except Exception:
            inference_degraded = True
            structured = {
                "hypothesis": "Session or cache invalidation race in auth middleware",
                "experiment_proposal": "Replay login flow with forced session rotation under load",
                "explanation": "Deterministic fallback — inference response was not valid JSON",
                "confidence": 0.35,
            }
    else:
        inference_degraded = True
        structured = {
            "hypothesis": "Session or cache invalidation race in auth middleware",
            "experiment_proposal": "Replay login flow with forced session rotation under load",
            "explanation": "Deterministic fallback — no generation-capable provider configured",
            "confidence": 0.35,
        }

    # --- Step 2: structured classification, Laya-first by default (see docstring above) ---
    classification: dict | None = None
    classification_provider: str | None = None
    if inference_router.classification_available:
        try:
            routed_c = await inference_router.classify(
                state=body.incident_summary, questions=_CLASSIFICATION_QUESTIONS
            )
            answers = routed_c.data.get("answers", {})
            severity = answers.get("severity", {}).get("choice")
            needs_action = answers.get("needs_immediate_action", {}).get("noul")
            if severity not in _ALLOWED_CLASSIFICATION_SEVERITIES:
                raise ValueError(f"unexpected severity {severity!r}")
            needs_action = float(needs_action)
            if not (0.0 <= needs_action <= 1.0):
                raise ValueError("needs_immediate_action out of range")
            # Sanitize the same way as Step 1: only these two coerced, validated fields
            # survive, regardless of what else the model's raw answer payload contained.
            classification = {
                "severity": str(severity),
                "needs_immediate_action_probability": needs_action,
            }
            classification_provider = routed_c.provider
        except Exception:
            classification = None
            classification_provider = None

    # Deterministic director still authoritative for scheduling decisions. This call is
    # identical regardless of what either model-assisted step above produced (or whether
    # either was even configured) — neither step's output is ever an input to it.
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
        "classification": classification,
        "classification_provider": classification_provider,
        "director_campaign_id": str(campaign.id),
        "director_state": campaign.state.value,
        "policy_note": "Scheduler/world/cost limits enforced server-side; model output is advisory only",
        "inference_degraded": inference_degraded,
        "inference_provider": served_by,
    }
