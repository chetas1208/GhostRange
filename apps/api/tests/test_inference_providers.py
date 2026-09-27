"""LayaLocalProvider / ExistingProvider unit tests against `httpx.MockTransport` (no real
network, no real model download) — covers required scenarios 1-5 and part of 7:

  1. Laya healthy
  2. Laya unavailable (connection refused)
  3. timeout
  4. malformed response
  5. structured output (via classify() — the real model's genuine capability)
  7. CPU-only configuration — health() downgrades a non-CPU device report

See test_laya_real_local_inference.py for the real, non-mocked end-to-end proof against an
actually-downloaded, actually-running local Laya model.
"""

from __future__ import annotations

import asyncio
import os

import httpx
import pytest

from ghostrange_api.config import Settings
from ghostrange_api.inference_providers import (
    LayaLocalProvider,
    ProviderError,
    ProviderErrorKind,
    ProviderStatus,
)


def _settings(monkeypatch, **env) -> Settings:
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "laya-local")
    monkeypatch.setenv("MODEL_BASE_URL", "http://127.0.0.1:8791")
    monkeypatch.setenv("MODEL_API_PROTOCOL", "native")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings.from_env()


def _provider(monkeypatch, handler, **env) -> LayaLocalProvider:
    settings = _settings(monkeypatch, **env)
    transport = httpx.MockTransport(handler)
    return LayaLocalProvider(settings, transport=transport)


# --- 1. Laya healthy -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_laya_healthy(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok", "loaded": ["english"], "device": "cpu"})

    provider = _provider(monkeypatch, handler)
    health = await provider.health()
    assert health.status == ProviderStatus.READY
    assert health.device == "CPU"
    assert health.provider == "laya-local"
    assert health.mode == "LOCAL"
    assert health.latency_ms is not None


# --- 2. Laya unavailable ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_laya_unavailable_connection_refused(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = _provider(monkeypatch, handler)
    health = await provider.health()
    assert health.status == ProviderStatus.OFFLINE
    assert "connection refused" in (health.detail or "")


@pytest.mark.asyncio
async def test_laya_not_active_for_generation_but_still_health_checkable(monkeypatch):
    """`available` (generation-gating) is False without INTELLIGENCE_PROVIDER=laya-local,
    but `health()` is a general reachability probe independent of that flag — see
    `classify_available`/health()'s own docstring in inference_providers.py — since
    classify() is default-on regardless of this flag."""
    settings = _settings(monkeypatch, INTELLIGENCE_PROVIDER="")
    provider = LayaLocalProvider(
        settings, transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"status": "ok", "device": "cpu"}))
    )
    assert provider.available is False
    assert provider.classify_available is True
    health = await provider.health()
    assert health.status == ProviderStatus.READY


@pytest.mark.asyncio
async def test_laya_health_not_configured_when_base_url_blank(monkeypatch):
    settings = _settings(monkeypatch, INTELLIGENCE_PROVIDER="", MODEL_BASE_URL="")
    provider = LayaLocalProvider(settings, transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    assert provider.classify_available is False
    health = await provider.health()
    assert health.status == ProviderStatus.NOT_CONFIGURED


# --- 3. timeout -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_laya_health_timeout(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(2.0)
        return httpx.Response(200, json={"status": "ok", "device": "cpu"})

    provider = _provider(monkeypatch, handler, LAYA_REQUEST_TIMEOUT_S="0.05")
    health = await provider.health()
    assert health.status == ProviderStatus.OFFLINE
    assert "timeout" in (health.detail or "").lower()


@pytest.mark.asyncio
async def test_laya_classify_timeout_raises_normalized_error(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(2.0)
        return httpx.Response(200, json={"answers": {}})

    provider = _provider(monkeypatch, handler, LAYA_REQUEST_TIMEOUT_S="0.05")
    with pytest.raises(ProviderError) as exc_info:
        await provider.classify(state="incident text", questions={"q": {"type": "noul", "instructions": "?"}})
    assert exc_info.value.kind == ProviderErrorKind.TIMEOUT


# --- 4. malformed response ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_laya_classify_malformed_json_body(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json at all")

    provider = _provider(monkeypatch, handler)
    with pytest.raises(ProviderError) as exc_info:
        await provider.classify(state="x", questions={"q": {"type": "noul", "instructions": "?"}})
    assert exc_info.value.kind == ProviderErrorKind.MALFORMED


@pytest.mark.asyncio
async def test_laya_classify_missing_answers_key_is_malformed(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"model": "laya", "usage": {}})  # no "answers"

    provider = _provider(monkeypatch, handler)
    with pytest.raises(ProviderError) as exc_info:
        await provider.classify(state="x", questions={"q": {"type": "noul", "instructions": "?"}})
    assert exc_info.value.kind == ProviderErrorKind.MALFORMED


@pytest.mark.asyncio
async def test_laya_generate_http_error_status_is_normalized(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal server error")

    settings = _settings(monkeypatch, MODEL_API_PROTOCOL="openai-compatible")
    provider = LayaLocalProvider(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError) as exc_info:
        await provider.generate(system="sys", user="hello")
    assert exc_info.value.kind == ProviderErrorKind.HTTP_ERROR


# --- 5. structured output (real Laya's genuine capability) ------------------------------


@pytest.mark.asyncio
async def test_laya_classify_returns_structured_output(monkeypatch):
    """Mirrors the real /v1/systemone response shape captured against the actually-running
    local model in test_laya_real_local_inference.py."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "laya-rl-agent",
                "answers": {
                    "severity": {
                        "type": "choice",
                        "choice": "high",
                        "probabilities": {"low": 0.03, "medium": 0.44, "high": 0.49, "critical": 0.03},
                        "confidence": 0.32,
                    },
                    "needs_rollback": {"type": "noul", "noul": 0.75, "confidence": 0.75},
                },
                "usage": {"input_tokens": 172, "output_tokens": 0},
            },
        )

    provider = _provider(monkeypatch, handler)
    result = await provider.classify(
        state="Incident report: repeated 500s after a deploy.",
        questions={
            "severity": {"type": "choice", "instructions": "How severe?", "criteria": {"low": "x", "high": "y"}},
            "needs_rollback": {"type": "noul", "instructions": "Rollback needed?"},
        },
    )
    assert result["answers"]["severity"]["choice"] == "high"
    assert 0.0 <= result["answers"]["needs_rollback"]["noul"] <= 1.0
    assert result["usage"]["output_tokens"] == 0  # non-autoregressive: never generates tokens


@pytest.mark.asyncio
async def test_laya_generate_is_unsupported_on_native_protocol(monkeypatch):
    """Real Laya cannot generate free text at all — generate()/structured_generate() must
    fail fast with `unsupported`, not silently fabricate a reply. This is what lets
    InferenceRouter correctly fall back to the existing provider for generation tasks."""
    provider = _provider(monkeypatch, lambda r: httpx.Response(200))
    with pytest.raises(ProviderError) as exc_info:
        await provider.generate(system="sys", user="summarize this incident")
    assert exc_info.value.kind == ProviderErrorKind.UNSUPPORTED

    with pytest.raises(ProviderError) as exc_info2:
        await provider.structured_generate(system="sys", user="propose a hypothesis")
    assert exc_info2.value.kind == ProviderErrorKind.UNSUPPORTED


# --- 7. CPU-only configuration ------------------------------------------------------------


@pytest.mark.asyncio
async def test_laya_health_downgrades_non_cpu_device_report(monkeypatch):
    """If the local runtime itself reports a non-CPU device (misconfigured operator), health
    must not claim READY — GhostRange requires CPU-only local inference."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok", "device": "cuda:0"})

    provider = _provider(monkeypatch, handler)
    health = await provider.health()
    assert health.status == ProviderStatus.DEGRADED
    assert "CPU" in (health.detail or "")


def test_no_gpu_cuda_config_path_exists(monkeypatch):
    """Static assertion: nothing in Settings or LayaLocalProvider exposes a settable
    GPU/CUDA device knob. CPU-only is enforced structurally (no config path to defeat it),
    not just by convention."""
    settings = _settings(monkeypatch)
    field_names = {f for f in settings.__dataclass_fields__}
    for name in field_names:
        assert "cuda" not in name.lower()
        assert "gpu" not in name.lower()

    import inspect

    from ghostrange_api import inference_providers

    src = inspect.getsource(inference_providers.LayaLocalProvider)
    # The only legitimate appearances of "cuda"/"gpu" are in the CPU-only *enforcement*
    # logic (rejecting a non-CPU device report) and comments — never as a value this class
    # could send to configure/request a GPU.
    assert 'device"] = "cuda' not in src
    assert '"gpu"' not in src.lower().replace("gpu-selecting", "").replace("gpu/cuda", "")
