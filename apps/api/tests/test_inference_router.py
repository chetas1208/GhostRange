"""InferenceRouter unit tests — required scenario 6 (fallback), plus provider-selection and
the default-on classify() ladder described in inference_router.py's module docstring.

Uses small hand-written InferenceProvider test doubles rather than the real Laya/Vultr
providers — the point here is the ROUTER's fallback logic, not any one provider's transport.
"""

from __future__ import annotations

import os

import pytest

from ghostrange_api.config import Settings
from ghostrange_api.inference_providers import (
    ExistingProvider,
    GenerationResult,
    LayaLocalProvider,
    ProviderError,
    ProviderErrorKind,
    ProviderHealth,
    ProviderStatus,
)
from ghostrange_api.inference_router import InferenceRouter, build_inference_router


class _StubProvider:
    def __init__(self, name: str, *, available: bool = True, fail: ProviderErrorKind | None = None) -> None:
        self.name = name
        self._available = available
        self._fail = fail
        self.calls = 0

    @property
    def available(self) -> bool:
        return self._available

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name, status=ProviderStatus.READY, device="CPU", model=None, mode="LOCAL", latency_ms=1
        )

    async def generate(self, *, system: str, user: str, max_tokens: int = 512) -> GenerationResult:
        self.calls += 1
        if self._fail is not None:
            raise ProviderError("stub failure", kind=self._fail, provider=self.name)
        return GenerationResult(text=f"generated-by-{self.name}", provider=self.name, model=None, latency_ms=1)

    async def structured_generate(self, *, system: str, user: str, max_tokens: int = 512) -> dict:
        self.calls += 1
        if self._fail is not None:
            raise ProviderError("stub failure", kind=self._fail, provider=self.name)
        return {"served_by": self.name}


class _StubClassifier(_StubProvider):
    @property
    def classify_available(self) -> bool:
        return self._available

    async def classify(self, *, state: str, questions: dict) -> dict:
        self.calls += 1
        if self._fail is not None:
            raise ProviderError("classify stub failure", kind=self._fail, provider=self.name)
        return {"answers": {"q": {"choice": f"classified-by-{self.name}"}}}


# --- 6. fallback (primary fails/times out -> secondary serves) ----------------------------


@pytest.mark.asyncio
async def test_generate_falls_back_to_secondary_on_primary_timeout():
    primary = _StubProvider("laya-local", fail=ProviderErrorKind.TIMEOUT)
    secondary = _StubProvider("existing")
    router = InferenceRouter(primary=primary, secondary=secondary)

    routed = await router.generate(system="s", user="u")

    assert routed.result.provider == "existing"
    assert routed.degraded is True
    assert primary.calls == 1
    assert secondary.calls == 1


@pytest.mark.asyncio
async def test_structured_generate_falls_back_to_secondary_on_primary_unsupported():
    primary = _StubProvider("laya-local", fail=ProviderErrorKind.UNSUPPORTED)
    secondary = _StubProvider("existing")
    router = InferenceRouter(primary=primary, secondary=secondary)

    routed = await router.structured_generate(system="s", user="u")

    assert routed.provider == "existing"
    assert routed.degraded is True
    assert routed.data == {"served_by": "existing"}


@pytest.mark.asyncio
async def test_generate_raises_when_primary_fails_and_no_secondary():
    primary = _StubProvider("existing", fail=ProviderErrorKind.OFFLINE)
    router = InferenceRouter(primary=primary, secondary=None)

    with pytest.raises(ProviderError) as exc_info:
        await router.generate(system="s", user="u")
    assert exc_info.value.kind == ProviderErrorKind.OFFLINE


@pytest.mark.asyncio
async def test_generate_uses_secondary_when_primary_not_available():
    primary = _StubProvider("laya-local", available=False)
    secondary = _StubProvider("existing")
    router = InferenceRouter(primary=primary, secondary=secondary)

    routed = await router.generate(system="s", user="u")

    assert routed.result.provider == "existing"
    assert primary.calls == 0  # never even attempted — not available


def test_active_provider_name_and_available():
    primary = _StubProvider("laya-local", available=False)
    secondary = _StubProvider("existing", available=True)
    router = InferenceRouter(primary=primary, secondary=secondary)
    assert router.active_provider_name == "existing"
    assert router.available is True

    router_none = InferenceRouter(primary=_StubProvider("x", available=False), secondary=None)
    assert router_none.active_provider_name == "not_configured"
    assert router_none.available is False


# --- default-on classify() ladder ----------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_prefers_laya_classifier_by_default():
    classifier = _StubClassifier("laya-local")
    fallback = _StubClassifier("existing")
    router = InferenceRouter(primary=fallback, secondary=None, classifier=classifier, classify_fallback=fallback)

    routed = await router.classify(state="x", questions={})

    assert routed.provider == "laya-local"
    assert routed.degraded is False
    assert fallback.calls == 0  # fallback never even attempted — Laya served fine


@pytest.mark.asyncio
async def test_classify_falls_back_when_laya_classifier_unreachable():
    classifier = _StubClassifier("laya-local", fail=ProviderErrorKind.OFFLINE)
    fallback = _StubClassifier("existing")
    router = InferenceRouter(primary=fallback, secondary=None, classifier=classifier, classify_fallback=fallback)

    routed = await router.classify(state="x", questions={})

    assert routed.provider == "existing"
    assert routed.degraded is True
    assert classifier.calls == 1
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_classify_raises_not_configured_when_nothing_available():
    router = InferenceRouter(primary=_StubProvider("x", available=False), secondary=None, classifier=None, classify_fallback=None)
    with pytest.raises(ProviderError) as exc_info:
        await router.classify(state="x", questions={})
    assert exc_info.value.kind == ProviderErrorKind.NOT_CONFIGURED


def test_classification_available_reflects_either_path():
    router = InferenceRouter(
        primary=_StubProvider("existing"),
        secondary=None,
        classifier=_StubClassifier("laya-local", available=False),
        classify_fallback=_StubClassifier("existing", available=True),
    )
    assert router.classification_available is True

    router_none = InferenceRouter(
        primary=_StubProvider("existing"),
        secondary=None,
        classifier=_StubClassifier("laya-local", available=False),
        classify_fallback=_StubClassifier("existing", available=False),
    )
    assert router_none.classification_available is False


# --- build_inference_router(): classify() is Laya-first BY DEFAULT, no opt-in required -----


def test_build_inference_router_wires_laya_classifier_without_any_opt_in(monkeypatch):
    """The point of this test: with INTELLIGENCE_PROVIDER completely unset (the out-of-the-
    box default) and no VULTR_INFERENCE_API_KEY, `build_inference_router` still wires a
    LayaLocalProvider in as the classifier — because MODEL_API_PROTOCOL defaults to "native"
    and MODEL_BASE_URL defaults to http://127.0.0.1:8791. Free-text generation still defaults
    to the existing provider, unaffected — this is the split described in
    inference_providers.py's module docstring."""
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.delenv("INTELLIGENCE_PROVIDER", raising=False)
    monkeypatch.delenv("VULTR_INFERENCE_API_KEY", raising=False)
    settings = Settings.from_env()
    assert settings.laya_active is False  # confirms no opt-in flag is set

    router = build_inference_router(settings)

    assert isinstance(router.primary, ExistingProvider)
    assert router.secondary is None
    assert isinstance(router.classifier, LayaLocalProvider)
    assert router.classifier.classify_available is True
    assert isinstance(router.classify_fallback, ExistingProvider)


def test_build_inference_router_omits_classifier_when_protocol_not_native(monkeypatch):
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.delenv("INTELLIGENCE_PROVIDER", raising=False)
    monkeypatch.setenv("MODEL_API_PROTOCOL", "openai-compatible")
    settings = Settings.from_env()
    router = build_inference_router(settings)
    assert router.classifier is None
