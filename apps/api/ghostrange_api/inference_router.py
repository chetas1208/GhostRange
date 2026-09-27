"""InferenceRouter — picks the active InferenceProvider and, only for the local Laya path,
falls back to the pre-existing Vultr provider on failure/timeout.

Fallback ladder (mirrors this project's *actual* existing convention, not an invented one):
  director_routes.py's `/v1/director/analyze` already wraps its single inference call in a
  try/except that degrades to a canned, deterministic proposal on ANY failure
  (`inference_degraded=True`) while the real, deterministic GhostDirector campaign keeps
  running untouched. This router adds exactly one rung *underneath* that existing rung:

      LOCAL_LAYA (if INTELLIGENCE_PROVIDER=laya-local)
            │ failure / timeout / unsupported
            ▼
      Existing provider (Vultr Serverless Inference), if configured
            │ failure / timeout / not configured
            ▼
      caller's own existing deterministic fallback (unchanged, e.g. director_routes.py)

When INTELLIGENCE_PROVIDER is unset/anything-else, the router's primary IS the existing
provider and there is no secondary — behavior is byte-for-byte what it was before this file
existed. GhostRange never depends on Laya being present or reachable.
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


class InferenceRouter:
    def __init__(self, primary: InferenceProvider, secondary: InferenceProvider | None = None) -> None:
        self._primary = primary
        self._secondary = secondary
        self.metrics: dict[str, int] = {
            "primary_attempts": 0,
            "primary_failures": 0,
            "fallback_attempts": 0,
            "fallback_failures": 0,
        }

    @property
    def primary(self) -> InferenceProvider:
        return self._primary

    @property
    def secondary(self) -> InferenceProvider | None:
        return self._secondary

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
        if self._primary.available:
            return await self._primary.health()
        if self._secondary is not None and self._secondary.available:
            return await self._secondary.health()
        # Neither configured — report the primary's own NOT_CONFIGURED health (still tells
        # the caller which provider *would* be primary once configured).
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


def build_inference_router(settings: Settings) -> InferenceRouter:
    """The one place `INTELLIGENCE_PROVIDER` is read to decide provider wiring. Everything
    else (director_routes.py, health_routes.py, main.py) calls this and talks to the
    resulting `InferenceRouter` — no other module branches on the env var's value."""
    existing = ExistingProvider(settings)
    if settings.laya_active:
        laya = LayaLocalProvider(settings)
        return InferenceRouter(primary=laya, secondary=existing)
    return InferenceRouter(primary=existing, secondary=None)
