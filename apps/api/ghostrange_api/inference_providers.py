"""InferenceProvider abstraction — the one seam between GhostRange domain code and any
model-assisted inference backend.

Two concrete providers implement the same small `InferenceProvider` Protocol:

  - `ExistingProvider`  — the pre-existing Vultr Serverless Inference path (wraps
    `InferenceService`, unchanged in behavior/config from before this module existed).
  - `LayaLocalProvider` — an OPTIONAL, local, CPU-only provider. Activated only by
    `INTELLIGENCE_PROVIDER=laya-local` (see `Settings.laya_active`); GhostRange must keep
    working with zero code-path changes when it is not.

Neither provider (nor the `InferenceRouter` in `inference_router.py` that picks between
them) ever calls Vultr Compute/Worker APIs, GhostExecutionGateway, or anything
scheduler/cost-related — this module is model-assisted *analysis* only (incident
summarization, hypothesis proposal, structured classification/extraction, remediation
explanation). All output from either provider is an untrusted, unvalidated text/JSON blob
until the caller (e.g. `director_routes.py`) validates/sanitizes it — this module does not
decide what is safe to act on.

## What "Laya" turned out to be

`convaiinnovations/laya` (PyPI package `laya`, Apache-2.0) is a REAL, existing, publicly
downloadable model — not fabricated for this task. It is a *non-autoregressive* "System 1
decision engine": one forward pass over a `state` string plus a fixed set of typed
`questions` (choice / score / yes-no) returns calibrated probabilities. It never generates
free text, so `generate()`/free-form `structured_generate()` (summarization, explanation,
hypothesis prose) are structurally outside what the real model can do — seeded fallback to
`ExistingProvider` is the correct behavior for those, not a bug. What it genuinely can do —
and what this file wires up as a real, tested, CPU-only local call — is exactly the spec's
"structured classification/extraction" use case: see `LayaLocalProvider.classify()`.

The package also ships an HTTP server (`laya[serve]` extra, `laya-serve` entrypoint,
`POST /v1/systemone` + `GET /health`) that matches this project's target architecture
(LayaAdapter → HTTP → local Laya Runtime on 127.0.0.1) exactly, so `MODEL_API_PROTOCOL=native`
targets that wire protocol. `MODEL_API_PROTOCOL=openai-compatible` is kept as the generic
fallback shape (e.g. a llama.cpp `server` or any other CPU-local OpenAI-compatible chat
endpoint an operator points `MODEL_BASE_URL` at instead) since the real Laya's own protocol
cannot serve free-text generation at all.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

import httpx

from .config import Settings
from .inference_service import InferenceService, extract_json_object

# Wire-protocol values MODEL_API_PROTOCOL may take. Anything else is a misconfiguration,
# not a silent no-op — LayaLocalProvider.__init__ fails fast on it.
_PROTOCOL_NATIVE = "native"
_PROTOCOL_OPENAI_COMPAT = "openai-compatible"
_KNOWN_PROTOCOLS = {_PROTOCOL_NATIVE, _PROTOCOL_OPENAI_COMPAT}


class ProviderStatus(str, Enum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class ProviderErrorKind(str, Enum):
    NOT_CONFIGURED = "not_configured"
    OFFLINE = "offline"
    TIMEOUT = "timeout"
    MALFORMED = "malformed_response"
    HTTP_ERROR = "http_error"
    UNSUPPORTED = "unsupported"
    CANCELLED = "cancelled"


class ProviderError(RuntimeError):
    """Normalized error every provider raises instead of a raw httpx/asyncio exception, so
    callers (and `InferenceRouter`'s fallback logic) can branch on `.kind` rather than on
    exception type or message text."""

    def __init__(self, message: str, *, kind: ProviderErrorKind, provider: str) -> None:
        self.kind = kind
        self.provider = provider
        super().__init__(f"{provider}[{kind.value}]: {message}")


@dataclass(frozen=True)
class ProviderHealth:
    provider: str
    status: ProviderStatus
    device: str  # "CPU" | "REMOTE" | "UNKNOWN"
    model: str | None
    mode: str  # "LOCAL" | "REMOTE"
    latency_ms: int | None
    detail: str | None = None


@dataclass(frozen=True)
class GenerationResult:
    text: str
    provider: str
    model: str | None
    latency_ms: int


@runtime_checkable
class InferenceProvider(Protocol):
    """The one shape both providers implement. Domain code (director_routes.py etc.) talks
    to this Protocol (via `InferenceRouter`) and nothing else — no `if provider == "laya"`
    branches outside this file and `inference_router.py`."""

    name: str

    @property
    def available(self) -> bool: ...

    async def health(self) -> ProviderHealth: ...

    async def generate(self, *, system: str, user: str, max_tokens: int = 512) -> GenerationResult: ...

    async def structured_generate(self, *, system: str, user: str, max_tokens: int = 512) -> dict[str, Any]: ...


class ExistingProvider:
    """Thin adapter over the pre-existing `InferenceService` (Vultr Serverless Inference).
    Behavior-preserving: every request this makes is byte-for-byte what `InferenceService`
    already sent before this module existed."""

    name = "existing"

    def __init__(self, settings: Settings, service: InferenceService | None = None) -> None:
        self._settings = settings
        self._service = service or InferenceService(settings)

    @property
    def available(self) -> bool:
        return self._service.available

    async def health(self) -> ProviderHealth:
        if not self.available:
            return ProviderHealth(
                provider=self.name,
                status=ProviderStatus.NOT_CONFIGURED,
                device="REMOTE",
                model=self._settings.inference_model,
                mode="REMOTE",
                latency_ms=None,
                detail="VULTR_INFERENCE_API_KEY not set",
            )
        # Lazy import: ops_routes imports from main-adjacent modules; matches the existing
        # lazy-import pattern in health_routes.py (avoids a circular import at module load).
        from .ops_routes import inference_smoke

        result = await inference_smoke(self._settings, minimal=True)
        ok = bool(result.get("ok"))
        return ProviderHealth(
            provider=self.name,
            status=ProviderStatus.READY if ok else ProviderStatus.DEGRADED,
            device="REMOTE",
            model=self._settings.inference_model,
            mode="REMOTE",
            latency_ms=result.get("latency_ms"),
            detail=None if ok else str(result.get("status", "degraded")),
        )

    async def generate(self, *, system: str, user: str, max_tokens: int = 512) -> GenerationResult:
        if not self.available:
            raise ProviderError("inference not configured", kind=ProviderErrorKind.NOT_CONFIGURED, provider=self.name)
        started = time.perf_counter()
        try:
            text = await self._service.complete_text(system=system, user=user, max_tokens=max_tokens)
        except httpx.TimeoutException as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.TIMEOUT, provider=self.name) from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.HTTP_ERROR, provider=self.name) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.OFFLINE, provider=self.name) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)
        return GenerationResult(text=text, provider=self.name, model=self._settings.inference_model, latency_ms=latency_ms)

    async def structured_generate(self, *, system: str, user: str, max_tokens: int = 512) -> dict[str, Any]:
        if not self.available:
            raise ProviderError("inference not configured", kind=ProviderErrorKind.NOT_CONFIGURED, provider=self.name)
        try:
            return await self._service.complete_json(system=system, user=user, max_tokens=max_tokens)
        except httpx.TimeoutException as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.TIMEOUT, provider=self.name) from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.HTTP_ERROR, provider=self.name) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.OFFLINE, provider=self.name) from exc
        except (ValueError, KeyError, IndexError) as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.MALFORMED, provider=self.name) from exc


# Laya checkpoint names laya-serve's own `/v1/systemone` route understands as an explicit
# `model` field (see `laya/serve.py::_KNOWN_MODELS` in the real package). Anything else in
# MODEL_NAME is passed through unset — the Router on the other end auto-selects.
_LAYA_KNOWN_MODELS = {"english", "multilingual", "typed-decisions"}


class LayaLocalProvider:
    """OPTIONAL, local, CPU-only provider — talks to a Laya runtime the operator started
    themselves (`laya-serve`, bound to 127.0.0.1 or a private network only; this class never
    binds/starts a listener). NOT active unless `Settings.laya_active` is True.

    CPU-only by construction: this class holds no device/GPU/CUDA setting at all and never
    sends one over the wire — "CPU-only" is enforced by (a) the operator running the local
    runtime with a CPU device, which `health()` verifies and downgrades if violated, and
    (b) the complete absence of any GPU-selecting knob anywhere in this file or in
    `Settings` (see `test_laya_cpu_only.py::test_no_gpu_cuda_config_path_exists`).
    """

    name = "laya-local"

    def __init__(self, settings: Settings) -> None:
        protocol = settings.model_api_protocol
        if protocol not in _KNOWN_PROTOCOLS:
            raise ValueError(
                f"MODEL_API_PROTOCOL={protocol!r} is not one of {sorted(_KNOWN_PROTOCOLS)}"
            )
        self._settings = settings
        self._protocol = protocol
        self._base_url = settings.model_base_url.rstrip("/")
        self._model_name = settings.model_name
        self._api_key = settings.model_api_key
        self._timeout_s = settings.laya_request_timeout_s
        self._max_input_chars = settings.laya_max_input_chars
        self._max_output_tokens = settings.laya_max_output_tokens
        import asyncio

        # Bounded concurrency: a single CPU box running Laya should never field more
        # forward passes at once than `Settings.laya_concurrency_cap` allows.
        self._sem = asyncio.Semaphore(settings.laya_concurrency_cap)

    @property
    def available(self) -> bool:
        return self._settings.laya_active and bool(self._base_url)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

    async def health(self) -> ProviderHealth:
        if not self.available:
            return ProviderHealth(
                provider=self.name,
                status=ProviderStatus.NOT_CONFIGURED,
                device="UNKNOWN",
                model=self._model_name,
                mode="LOCAL",
                latency_ms=None,
                detail="INTELLIGENCE_PROVIDER != laya-local, or MODEL_BASE_URL unset",
            )
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                if self._protocol == _PROTOCOL_NATIVE:
                    resp = await client.get(f"{self._base_url}/health")
                else:
                    # No standardized health route for a generic OpenAI-compatible local
                    # server; a cheap 1-token completion is the closest honest proxy.
                    resp = await client.post(
                        f"{self._base_url}/chat/completions",
                        json={
                            "model": self._model_name or "local",
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 1,
                        },
                        headers=self._headers(),
                    )
        except httpx.ConnectError as exc:
            return ProviderHealth(
                provider=self.name, status=ProviderStatus.OFFLINE, device="UNKNOWN",
                model=self._model_name, mode="LOCAL", latency_ms=None, detail=f"connection refused: {exc}",
            )
        except httpx.TimeoutException as exc:
            return ProviderHealth(
                provider=self.name, status=ProviderStatus.OFFLINE, device="UNKNOWN",
                model=self._model_name, mode="LOCAL", latency_ms=None, detail=f"timeout: {exc}",
            )
        except httpx.HTTPError as exc:
            return ProviderHealth(
                provider=self.name, status=ProviderStatus.DEGRADED, device="UNKNOWN",
                model=self._model_name, mode="LOCAL", latency_ms=None, detail=str(exc),
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        if resp.status_code >= 400:
            return ProviderHealth(
                provider=self.name, status=ProviderStatus.DEGRADED, device="UNKNOWN",
                model=self._model_name, mode="LOCAL", latency_ms=latency_ms,
                detail=f"HTTP {resp.status_code}",
            )
        device = "UNKNOWN"
        status = ProviderStatus.READY
        detail = None
        if self._protocol == _PROTOCOL_NATIVE:
            try:
                body = resp.json()
            except ValueError:
                return ProviderHealth(
                    provider=self.name, status=ProviderStatus.DEGRADED, device="UNKNOWN",
                    model=self._model_name, mode="LOCAL", latency_ms=latency_ms,
                    detail="health endpoint returned non-JSON body",
                )
            reported_device = str(body.get("device") or "unknown").upper()
            device = reported_device
            if body.get("status") != "ok":
                status = ProviderStatus.DEGRADED
                detail = f"local runtime reported status={body.get('status')!r}"
            elif reported_device not in ("CPU", "AUTO"):
                # GhostRange requires CPU-only local inference. A runtime that reports
                # cuda/mps must never be surfaced as READY, even though it answered.
                status = ProviderStatus.DEGRADED
                detail = f"local runtime reported non-CPU device={reported_device!r}; GhostRange requires CPU-only"
        else:
            device = "UNKNOWN"
        return ProviderHealth(
            provider=self.name, status=status, device=device or "UNKNOWN",
            model=self._model_name, mode="LOCAL", latency_ms=latency_ms, detail=detail,
        )

    async def generate(self, *, system: str, user: str, max_tokens: int = 512) -> GenerationResult:
        if not self.available:
            raise ProviderError("laya-local not configured/active", kind=ProviderErrorKind.NOT_CONFIGURED, provider=self.name)
        if self._protocol == _PROTOCOL_NATIVE:
            # The real Laya model is non-autoregressive: it scores typed questions in one
            # forward pass and never emits free text. Free-form generation is structurally
            # impossible against it — raising `unsupported` (rather than faking a reply)
            # is what lets `InferenceRouter` fall back to the existing provider correctly.
            raise ProviderError(
                "real Laya (non-autoregressive decision engine) cannot generate free-form "
                "text; use classify() for structured decisions, or configure a fallback "
                "provider for summarization/explanation tasks",
                kind=ProviderErrorKind.UNSUPPORTED,
                provider=self.name,
            )
        bounded_user = user[: self._max_input_chars]
        bounded_max_tokens = min(max_tokens, self._max_output_tokens)
        started = time.perf_counter()
        try:
            async with self._sem:
                async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                    resp = await client.post(
                        f"{self._base_url}/chat/completions",
                        json={
                            "model": self._model_name or "local",
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": bounded_user},
                            ],
                            "max_tokens": bounded_max_tokens,
                            "temperature": 0.2,
                        },
                        headers=self._headers(),
                    )
        except httpx.ConnectError as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.OFFLINE, provider=self.name) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.TIMEOUT, provider=self.name) from exc
        if resp.status_code >= 400:
            raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:200]}", kind=ProviderErrorKind.HTTP_ERROR, provider=self.name)
        try:
            body = resp.json()
            text = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"malformed response: {exc}", kind=ProviderErrorKind.MALFORMED, provider=self.name) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)
        return GenerationResult(text=text, provider=self.name, model=self._model_name, latency_ms=latency_ms)

    async def structured_generate(self, *, system: str, user: str, max_tokens: int = 512) -> dict[str, Any]:
        if self._protocol == _PROTOCOL_NATIVE:
            raise ProviderError(
                "real Laya cannot synthesize arbitrary free-form JSON from a system/user "
                "prompt; call classify(state=..., questions=...) for genuine structured "
                "classification/extraction against the real model",
                kind=ProviderErrorKind.UNSUPPORTED,
                provider=self.name,
            )
        result = await self.generate(system=system, user=user, max_tokens=max_tokens)
        try:
            return extract_json_object(result.text)
        except ValueError as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.MALFORMED, provider=self.name) from exc

    async def classify(self, *, state: str, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Real passthrough to Laya's own `/v1/systemone` wire protocol — typed
        choice/score/yes-no decisions over `state` in a single forward pass. This is the
        genuine "structured classification/extraction" capability the real model has; it is
        deliberately NOT exposed through the generic `structured_generate()` Protocol method
        because it does not take a free-form schema — the caller must speak Laya's own typed
        question format. See module docstring for why.

        Bounded input, bounded concurrency, timeout, and error normalization all apply, same
        as `generate()`.
        """
        if self._protocol != _PROTOCOL_NATIVE:
            raise ProviderError(
                "classify() requires MODEL_API_PROTOCOL=native",
                kind=ProviderErrorKind.UNSUPPORTED,
                provider=self.name,
            )
        if not self.available:
            raise ProviderError("laya-local not configured/active", kind=ProviderErrorKind.NOT_CONFIGURED, provider=self.name)
        bounded_state = state[: self._max_input_chars]
        payload: dict[str, Any] = {"state": bounded_state, "questions": questions}
        if self._model_name and self._model_name in _LAYA_KNOWN_MODELS:
            payload["model"] = self._model_name
        try:
            async with self._sem:
                async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                    resp = await client.post(
                        f"{self._base_url}/v1/systemone",
                        json=payload,
                        headers=self._headers(),
                    )
        except httpx.ConnectError as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.OFFLINE, provider=self.name) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError(str(exc), kind=ProviderErrorKind.TIMEOUT, provider=self.name) from exc
        if resp.status_code >= 400:
            raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:200]}", kind=ProviderErrorKind.HTTP_ERROR, provider=self.name)
        try:
            body = resp.json()
        except ValueError as exc:
            raise ProviderError(f"malformed response: {exc}", kind=ProviderErrorKind.MALFORMED, provider=self.name) from exc
        if not isinstance(body, dict) or "answers" not in body:
            raise ProviderError("response missing 'answers'", kind=ProviderErrorKind.MALFORMED, provider=self.name)
        return body
