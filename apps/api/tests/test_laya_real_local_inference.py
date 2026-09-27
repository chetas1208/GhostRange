"""REAL, non-mocked, end-to-end proof: an actually-downloaded, actually-running local Laya
model, queried over real HTTP, through this repo's own `LayaLocalProvider.classify()` code
(not a hand-rolled curl call) — CPU-only, bound to 127.0.0.1.

This is deliberately separate from test_inference_providers.py (which uses
`httpx.MockTransport` and makes no real network/model call at all). Per the hard
requirement given for this task — "do not claim Laya integration is working until a real
local inference request succeeds end-to-end" — this file is the actual evidence.

What "Laya" turned out to be, concretely: the real PyPI package `laya` (Apache-2.0,
`pip install "laya[serve]"`), wrapping the real Hugging Face checkpoint
`convaiinnovations/laya` (ModernBERT-large, 421M params, English). It is a non-autoregressive
"System 1 decision engine" — no text generation, only typed choice/score/yes-no decisions in
a single forward pass — which is exactly what `LayaLocalProvider.classify()` exercises here.

Skipped unless a real `laya-serve` instance is already reachable at
`LAYA_LIVE_TEST_BASE_URL` (default `http://127.0.0.1:8791`), the same way
test_inference_worker_pool.py skips unless `VULTR_INFERENCE_API_KEY` is set for real Vultr
calls — this suite does not itself download an ~800MB model checkpoint or spawn a server
process as a side effect of `pytest` running in CI. To actually run this test:

    pip install "laya[serve]"
    LAYA_HOST=127.0.0.1 LAYA_PORT=8791 LAYA_DEVICE=cpu LAYA_MODELS=english laya-serve &
    pytest apps/api/tests/test_laya_real_local_inference.py -v

(That is exactly the sequence that was actually run, once, to produce the real answers
quoted in this file's assertions' neighborhood — see the task's final report for the raw
`curl` transcript.)
"""

from __future__ import annotations

import os

import httpx
import pytest

from ghostrange_api.config import Settings
from ghostrange_api.inference_providers import LayaLocalProvider, ProviderStatus

_BASE_URL = os.environ.get("LAYA_LIVE_TEST_BASE_URL", "http://127.0.0.1:8791")


def _laya_server_reachable() -> bool:
    try:
        resp = httpx.get(f"{_BASE_URL}/health", timeout=2.0)
        return resp.status_code == 200 and resp.json().get("status") == "ok"
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _laya_server_reachable(),
    reason=(
        f"no real laya-serve instance reachable at {_BASE_URL} — see this file's module "
        "docstring for the exact command to start one (pip install laya[serve]; laya-serve)"
    ),
)


def _real_provider(monkeypatch) -> LayaLocalProvider:
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "laya-local")
    monkeypatch.setenv("MODEL_BASE_URL", _BASE_URL)
    monkeypatch.setenv("MODEL_API_PROTOCOL", "native")
    monkeypatch.setenv("MODEL_NAME", "english")
    settings = Settings.from_env()
    # No `transport=` override here — this is the one test in the whole suite that makes a
    # genuine outbound HTTP call to a genuine running model process.
    return LayaLocalProvider(settings)


@pytest.mark.asyncio
async def test_real_laya_health_reports_cpu_ready(monkeypatch):
    provider = _real_provider(monkeypatch)
    health = await provider.health()

    assert health.status == ProviderStatus.READY
    assert health.device == "CPU"
    assert health.provider == "laya-local"
    assert health.latency_ms is not None and health.latency_ms >= 0


@pytest.mark.asyncio
async def test_real_laya_classify_end_to_end_incident_severity(monkeypatch):
    """The actual real-world call this integration exists to prove: a real incident
    description, scored for real by the real downloaded model, on CPU, over real HTTP,
    through this repo's own provider code — not a stub, not a fixture replay."""
    provider = _real_provider(monkeypatch)

    state = (
        "Incident report: repeated 500 errors from the auth-service after a deploy at "
        "14:02 UTC. Error rate spiked from 0.1% to 22% within 3 minutes. Rollback has not "
        "yet been performed."
    )
    questions = {
        "severity": {
            "type": "choice",
            "instructions": "How severe is this incident?",
            "criteria": {
                "low": "minor, no user impact",
                "medium": "partial degradation",
                "high": "major user-facing outage",
                "critical": "total outage or data risk",
            },
        },
        "needs_rollback": {
            "type": "noul",
            "instructions": "Does this incident likely require an immediate rollback of the recent deploy?",
        },
    }

    result = await provider.classify(state=state, questions=questions)

    # Real response shape from the real model (captured verbatim against this exact
    # request during this task — see the final report): {"model": "laya-rl-agent",
    # "answers": {"severity": {"choice": "high", ...}, "needs_rollback": {"noul": 0.7549,
    # ...}}, "usage": {"input_tokens": 172, "output_tokens": 0}}
    assert "answers" in result
    severity = result["answers"]["severity"]
    assert severity["choice"] in {"low", "medium", "high", "critical"}
    assert 0.0 <= severity["probabilities"][severity["choice"]] <= 1.0

    rollback = result["answers"]["needs_rollback"]
    assert 0.0 <= rollback["noul"] <= 1.0

    # Non-autoregressive: real Laya never generates tokens, even for a real call.
    assert result["usage"]["output_tokens"] == 0
    assert result["usage"]["input_tokens"] > 0


@pytest.mark.asyncio
async def test_real_laya_classify_is_deterministic_across_two_real_calls(monkeypatch):
    """Same real state + questions, two separate real HTTP round trips to the real model —
    the point being this is genuinely re-callable, not a one-off fluke."""
    provider = _real_provider(monkeypatch)
    state = "Database connection pool exhausted; p99 latency up 40x for 90 seconds."
    questions = {
        "severity": {
            "type": "choice",
            "instructions": "How severe is this incident?",
            "criteria": {"low": "minor", "medium": "moderate", "high": "severe", "critical": "catastrophic"},
        }
    }
    first = await provider.classify(state=state, questions=questions)
    second = await provider.classify(state=state, questions=questions)
    assert first["answers"]["severity"]["choice"] == second["answers"]["severity"]["choice"]
