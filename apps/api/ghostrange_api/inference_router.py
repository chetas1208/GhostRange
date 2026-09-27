"""InferenceRouter — picks the active InferenceProvider for free-text generation, and
separately runs a default-on Laya-first path for structured classification/extraction (the
one thing the real Laya model genuinely does — see inference_providers.py's module
docstring for why these two are split).

Free-text fallback ladder (mirrors this project's *actual* existing convention, not an
invented one): director_routes.py's `/v1/director/analyze` already wraps its single
inference call in a try/except that degrades to a canned, deterministic proposal on ANY
failure (`inference_degraded=True`) while the real, deterministic GhostDirector campaign
keeps running untouched. `generate()`/`structured_generate()` add exactly one rung
*underneath* that existing rung:

      primary (existing provider unless INTELLIGENCE_PROVIDER=laya-local — and even then,
               Laya immediately raises `unsupported` for these two methods, so it never
               actually serves a generation request; see LayaLocalProvider.generate())
            │ failure / timeout / unsupported
            ▼
      secondary (existing provider, only present when Laya was primary)
            │ failure / timeout / not configured
            ▼
      caller's own existing deterministic fallback (unchanged, e.g. director_routes.py)

`classify()` fallback ladder — DEFAULT-ON, no INTELLIGENCE_PROVIDER opt-in required:

      Laya classify() (whenever MODEL_API_PROTOCOL=native + MODEL_BASE_URL reachable —
                        true out of the box, since both already default to exactly that)
            │ failure / timeout / unreachable
            ▼
      Existing provider's classify() (prompted-JSON translation over the same LLM call
                                       path everything else in this codebase already uses)
            │ failure / not configured
            ▼
      caller decides what "no classification available" means for its own response
      (director_routes.py simply omits those fields — see _ALLOWED_PROPOSAL_KEYS)

When INTELLIGENCE_PROVIDER is unset/anything-else, `generate()`/`structured_generate()`
behavior is byte-for-byte what it was before this file existed — GhostRange never depends
on Laya being present or reachable for those. `classify()` is additive: nothing that existed
before this file called it, so there is nothing for it to change when Laya is absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import Settings
from .inference_providers import (
    ExistingProvider,
    GenerationResult,
    InferenceProvider,
    LayaLocalProvider,
    ProviderError,
    ProviderErrorKind,
    ProviderHealth,
)


@dataclass(frozen=True)
class RoutedGeneration:
    result: GenerationResult
    degraded: bool  # True when the primary failed and the secondary served instead


@dataclass(frozen=True)
class RoutedStructured:
    data: dict[str, Any]
    provider: str
    degraded: bool


@dataclass(frozen=True)
class RoutedClassification:
    data: dict[str, Any]
    provider: str
    degraded: bool  # True when Laya was unreachable and the existing-provider fallback served


class InferenceRouter:
    def __init__(
        self,
        primary: InferenceProvider,
        secondary: InferenceProvider | None = None,
        *,
        classifier: LayaLocalProvider | None = None,
        classify_fallback: ExistingProvider | None = None,
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        # Separate from primary/secondary: classify() defaults Laya-first regardless of
        # which provider is "primary" for generation (see module docstring).
        self._classifier = classifier
        self._classify_fallback = classify_fallback
        self.metrics: dict[str, int] = {
            "primary_attempts": 0,
            "primary_failures": 0,
            "fallback_attempts": 0,
            "fallback_failures": 0,
            "classify_laya_attempts": 0,
            "classify_laya_failures": 0,
            "classify_fallback_attempts": 0,
            "classify_fallback_failures": 0,
        }

    @property
    def primary(self) -> InferenceProvider:
        return self._primary

    @property
    def secondary(self) -> InferenceProvider | None:
        return self._secondary

    @property
    def classifier(self) -> "LayaLocalProvider | None":
        return self._classifier

    @property
    def classify_fallback(self) -> "ExistingProvider | None":
        return self._classify_fallback

    @property
    def available(self) -> bool:
        return bool(self._primary.available or (self._secondary and self._secondary.available))

    @property
    def active_provider_name(self) -> str:
        if self._primary.available:
            return self._primary.name
        if self._secondary and self._secondary.available:
            return self._secondary.name
        return "not_configured"

    async def health(self) -> ProviderHealth:
        """Reported health for the system-status/health surface (see health_routes.py). Not
        the same gate as `available`: this also reflects the default-on Laya classifier when
        it's the only thing actually configured — otherwise a from-scratch install (no
        VULTR_INFERENCE_API_KEY, no INTELLIGENCE_PROVIDER) with a real local Laya runtime
        running would report "not configured" despite classify() genuinely working."""
        if self._primary.available:
            return await self._primary.health()
        if self._secondary is not None and self._secondary.available:
            return await self._secondary.health()
        if self._classifier is not None and self._classifier.classify_available:
            return await self._classifier.health()
        # Nothing configured at all — report the primary's own NOT_CONFIGURED health (still
        # tells the caller which provider *would* be primary once configured).
        return await self._primary.health()

    async def generate(self, *, system: str, user: str, max_tokens: int = 512) -> RoutedGeneration:
        if self._primary.available:
            self.metrics["primary_attempts"] += 1
            try:
                result = await self._primary.generate(system=system, user=user, max_tokens=max_tokens)
                return RoutedGeneration(result=result, degraded=False)
            except ProviderError:
                self.metrics["primary_failures"] += 1
                if self._secondary is None or not self._secondary.available:
                    raise
                # fall through to secondary
            except Exception:
                self.metrics["primary_failures"] += 1
                if self._secondary is None or not self._secondary.available:
                    raise
        if self._secondary is not None and self._secondary.available:
            self.metrics["fallback_attempts"] += 1
            try:
                result = await self._secondary.generate(system=system, user=user, max_tokens=max_tokens)
                return RoutedGeneration(result=result, degraded=True)
            except Exception:
                self.metrics["fallback_failures"] += 1
                raise
        raise ProviderError("no inference provider configured", kind=ProviderErrorKind.NOT_CONFIGURED, provider="router")

    async def structured_generate(self, *, system: str, user: str, max_tokens: int = 512) -> RoutedStructured:
        if self._primary.available:
            self.metrics["primary_attempts"] += 1
            try:
                data = await self._primary.structured_generate(system=system, user=user, max_tokens=max_tokens)
                return RoutedStructured(data=data, provider=self._primary.name, degraded=False)
            except ProviderError:
                self.metrics["primary_failures"] += 1
                if self._secondary is None or not self._secondary.available:
                    raise
            except Exception:
                self.metrics["primary_failures"] += 1
                if self._secondary is None or not self._secondary.available:
                    raise
        if self._secondary is not None and self._secondary.available:
            self.metrics["fallback_attempts"] += 1
            try:
                data = await self._secondary.structured_generate(system=system, user=user, max_tokens=max_tokens)
                return RoutedStructured(data=data, provider=self._secondary.name, degraded=True)
            except Exception:
                self.metrics["fallback_failures"] += 1
                raise
        raise ProviderError("no inference provider configured", kind=ProviderErrorKind.NOT_CONFIGURED, provider="router")

    @property
    def classification_available(self) -> bool:
        laya_ok = self._classifier is not None and self._classifier.classify_available
        fallback_ok = self._classify_fallback is not None and self._classify_fallback.available
        return bool(laya_ok or fallback_ok)

    async def classify(self, *, state: str, questions: dict[str, dict[str, Any]]) -> RoutedClassification:
        """Default-on structured classification/extraction: tries the real local Laya model
        FIRST whenever it's reachable (no opt-in required — see module docstring), and
        falls back to the existing provider's own (LLM-prompted) classification when it
        isn't. Raises `ProviderError(kind=NOT_CONFIGURED)` only when neither path is even
        configured — callers should treat that as "no classification available" and degrade
        their own response accordingly (see director_routes.py)."""
        if self._classifier is not None and self._classifier.classify_available:
            self.metrics["classify_laya_attempts"] += 1
            try:
                data = await self._classifier.classify(state=state, questions=questions)
                return RoutedClassification(data=data, provider=self._classifier.name, degraded=False)
            except Exception:
                self.metrics["classify_laya_failures"] += 1
                # fall through to the existing-provider translation below
        if self._classify_fallback is not None and self._classify_fallback.available:
            self.metrics["classify_fallback_attempts"] += 1
            try:
                data = await self._classify_fallback.classify(state=state, questions=questions)
                return RoutedClassification(data=data, provider=self._classify_fallback.name, degraded=True)
            except Exception:
                self.metrics["classify_fallback_failures"] += 1
                raise
        raise ProviderError("no classification provider configured", kind=ProviderErrorKind.NOT_CONFIGURED, provider="router")


def build_inference_router(settings: Settings) -> InferenceRouter:
    """The one place `INTELLIGENCE_PROVIDER`/`MODEL_*` are read to decide provider wiring.
    Everything else (director_routes.py, health_routes.py, main.py) calls this and talks to
    the resulting `InferenceRouter` — no other module branches on those env vars.

    Free-text generation stays keyed off `INTELLIGENCE_PROVIDER=laya-local` (and, even then,
    always ends up served by the existing provider — real Laya cannot generate free text at
    all). Structured classification (`classify()`) is wired Laya-first by default,
    independent of that flag — see the module docstring's two fallback ladders."""
    existing = ExistingProvider(settings)
    # classify()'s Laya-first default does not require INTELLIGENCE_PROVIDER=laya-local —
    # only that a native-protocol local runtime is configured, which is the out-of-the-box
    # default (MODEL_BASE_URL=http://127.0.0.1:8791, MODEL_API_PROTOCOL=native). One
    # `LayaLocalProvider` instance is reused for both roles when `laya_active` is also set.
    classifier = LayaLocalProvider(settings) if settings.model_api_protocol == "native" else None
    if settings.laya_active:
        laya = classifier if classifier is not None else LayaLocalProvider(settings)
        return InferenceRouter(primary=laya, secondary=existing, classifier=laya, classify_fallback=existing)
    return InferenceRouter(primary=existing, secondary=None, classifier=classifier, classify_fallback=existing)
