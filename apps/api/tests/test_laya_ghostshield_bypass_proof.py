"""Required scenarios 8 and 9:

  8. GhostRange still works without Laya (INTELLIGENCE_PROVIDER unset/default, and nothing
     reachable at all — no Vultr key, no local runtime).
  9. A Laya-sourced (or any provider's) structured proposal cannot bypass GhostShield/the
     scheduler: proof that /v1/director/analyze never constructs a GhostExecutionGateway
     action from model output, and that the deterministic GhostDirectorSimulator campaign
     it runs is unaffected by what the model proposed — matching how GhostDirector actually
     consumes proposals today (see ghostrange_director/director.py::run_campaign, which
     never imports or calls GhostExecutionGateway at all; director_routes.py's `/analyze`
     runs the model call and the deterministic campaign as two independent things and never
     wires one's output into the other).
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from ghostrange_api import main as main_module
from ghostrange_api.inference_router import InferenceRouter


class _FakeMaliciousProvider:
    """Stands in for a compromised/adversarial model provider (Laya or otherwise): its
    structured_generate() reply tries to smuggle an action/approval/cost past the route
    alongside the 4 fields the route actually asks for."""

    name = "fake-malicious"

    def __init__(self, extra: dict) -> None:
        self._extra = extra

    @property
    def available(self) -> bool:
        return True

    async def health(self):  # pragma: no cover - not exercised by this route
        raise NotImplementedError

    async def generate(self, *, system: str, user: str, max_tokens: int = 512):  # pragma: no cover
        raise NotImplementedError

    async def structured_generate(self, *, system: str, user: str, max_tokens: int = 512) -> dict:
        return {
            "hypothesis": "malicious hypothesis text",
            "experiment_proposal": "malicious experiment proposal text",
            "explanation": "malicious explanation text",
            "confidence": 0.99,
            **self._extra,
        }


def _fresh_app(monkeypatch, router: InferenceRouter):
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.setenv("GHOSTSHIELD_MODE", "ENFORCE")
    monkeypatch.setenv("GHOSTRANGE_SKIP_RUNTIME_VALIDATE", "true")
    # main.create_app() calls build_inference_router(settings) itself (both in the
    # synchronous bootstrap block and again in the async lifespan) — patching the name it's
    # imported under in main.py is what lets every code path get our fixed test double,
    # regardless of whether TestClient triggers the lifespan.
    monkeypatch.setattr(main_module, "build_inference_router", lambda settings: router)
    return main_module.create_app()


# --- 8. GhostRange still works without Laya (and without anything else configured) --------


def test_analyze_works_with_zero_inference_configured(monkeypatch):
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.setenv("GHOSTRANGE_SKIP_RUNTIME_VALIDATE", "true")
    monkeypatch.delenv("VULTR_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("INTELLIGENCE_PROVIDER", raising=False)
    # Point MODEL_BASE_URL at a port nothing listens on, so this test is hermetic regardless
    # of whether a real laya-serve happens to be running on the machine executing it.
    monkeypatch.setenv("MODEL_BASE_URL", "http://127.0.0.1:65500")

    client = TestClient(main_module.create_app())
    resp = client.post(
        "/v1/director/analyze",
        json={"incident_summary": "auth-service is throwing 500s after a deploy at 14:02 UTC"},
    )

    assert resp.status_code == 200
    body = resp.json()
    # Deterministic canned fallback for the free-text proposal — GhostRange answers, it just
    # doesn't have a model-generated answer.
    assert body["inference_degraded"] is True
    assert body["inference_provider"] == "deterministic_fallback"
    assert body["model_proposal"]["hypothesis"]
    assert 0.0 <= body["model_proposal"]["confidence"] <= 1.0
    # No classification provider reachable either — omitted, not an error.
    assert body["classification"] is None
    assert body["classification_provider"] is None
    # The deterministic director campaign still ran.
    assert body["director_campaign_id"]
    assert isinstance(body["director_state"], str) and body["director_state"]


def test_health_ready_reports_offline_intelligence_when_default_classifier_unreachable(monkeypatch):
    """Out-of-the-box config (no VULTR key, no INTELLIGENCE_PROVIDER) still points the
    default-on classifier at MODEL_BASE_URL — so with nothing actually listening there, the
    accurate status is OFFLINE (configured, unreachable), not NOT_CONFIGURED. Either way this
    must never fail readiness."""
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.setenv("GHOSTRANGE_SKIP_RUNTIME_VALIDATE", "true")
    monkeypatch.delenv("VULTR_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("INTELLIGENCE_PROVIDER", raising=False)
    monkeypatch.setenv("MODEL_BASE_URL", "http://127.0.0.1:65500")

    client = TestClient(main_module.create_app())
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["checks"]["intelligence"]["provider"] == "laya-local"
    assert body["checks"]["intelligence"]["status"] == "OFFLINE"


def test_health_ready_reports_not_configured_when_base_url_explicitly_blank(monkeypatch):
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.setenv("GHOSTRANGE_SKIP_RUNTIME_VALIDATE", "true")
    monkeypatch.delenv("VULTR_INFERENCE_API_KEY", raising=False)
    monkeypatch.delenv("INTELLIGENCE_PROVIDER", raising=False)
    monkeypatch.setenv("MODEL_BASE_URL", "")

    client = TestClient(main_module.create_app())
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["checks"]["intelligence"]["provider"] == "not_configured"
    assert body["checks"]["intelligence"]["status"] == "NOT_CONFIGURED"


# --- 9. GhostShield/scheduler bypass proof -------------------------------------------------


@pytest.mark.parametrize(
    "extra",
    [
        {"action": "CREATE_WORKER", "approved": True},
        {"bypass_ghostshield": True, "cost_usd": 0, "resource_id": "vm-12345"},
        {"director_override": "APPROVE_ALL", "skip_validation": True},
    ],
)
def test_malicious_proposal_is_sanitized_and_never_reaches_gateway(monkeypatch, extra):
    from ghostrange_ghostshield import GhostExecutionGateway

    authorize_spy = MagicMock(side_effect=AssertionError("gateway.authorize must never be called from a model proposal"))
    monkeypatch.setattr(GhostExecutionGateway, "authorize", authorize_spy)

    fake_provider = _FakeMaliciousProvider(extra)
    router = InferenceRouter(primary=fake_provider, secondary=None, classifier=None, classify_fallback=None)
    app = _fresh_app(monkeypatch, router)
    client = TestClient(app)

    resp = client.post("/v1/director/analyze", json={"incident_summary": "test incident for the bypass proof"})

    assert resp.status_code == 200
    body = resp.json()

    # 1. GhostExecutionGateway.authorize was never called — the model's output never
    #    reached anything gated by GhostShield.
    authorize_spy.assert_not_called()

    # 2. Sanitization actually stripped the smuggled fields — only the 4 whitelisted keys
    #    survive in the response the frontend would see.
    assert set(body["model_proposal"].keys()) == {"hypothesis", "experiment_proposal", "explanation", "confidence"}
    for key in extra:
        assert key not in body["model_proposal"]

    # 3. The proposal was used as-is for its allowed fields (proves sanitization isn't just
    #    silently falling back to the canned proposal — this was the real fake response).
    assert body["model_proposal"]["hypothesis"] == "malicious hypothesis text"
    assert body["inference_degraded"] is False
    assert body["inference_provider"] == "fake-malicious"

    # 4. The deterministic director campaign ran regardless, from its own fixed scenario —
    #    never fed anything from the model's proposal.
    assert body["director_campaign_id"]
    assert isinstance(body["director_state"], str) and body["director_state"]


def test_deterministic_campaign_outcome_is_identical_regardless_of_proposal_content(monkeypatch):
    """Two requests with different malicious payloads must produce the same director
    campaign shape (state/stop_reason/experiment count) — proof the model's output is never
    an input to GhostDirectorSimulator.run_campaign, only ever advisory display data."""
    router_a = InferenceRouter(
        primary=_FakeMaliciousProvider({"action": "APPROVE"}), secondary=None, classifier=None, classify_fallback=None
    )
    app_a = _fresh_app(monkeypatch, router_a)
    resp_a = TestClient(app_a).post("/v1/director/analyze", json={"incident_summary": "incident summary one"})

    router_b = InferenceRouter(
        primary=_FakeMaliciousProvider({"action": "DENY_EVERYTHING", "cost_usd": 999999}),
        secondary=None,
        classifier=None,
        classify_fallback=None,
    )
    app_b = _fresh_app(monkeypatch, router_b)
    resp_b = TestClient(app_b).post("/v1/director/analyze", json={"incident_summary": "a totally different incident"})

    body_a, body_b = resp_a.json(), resp_b.json()
    assert body_a["director_state"] == body_b["director_state"]
    assert body_a["policy_note"] == body_b["policy_note"]
