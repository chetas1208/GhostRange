"""Single mediated path for protected provider effects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Generic, TypeVar

from ghostrange_contracts.ghostshield_m17 import (
    ActionPermitV1,
    AuthorizationContextV1,
    AuthorizationVerdict,
    CanonicalActionV1,
    GhostShieldMode,
)

from .policy_engine import GhostShieldPolicyEngine

T = TypeVar("T")


class GatewayError(RuntimeError):
    pass


@dataclass
class GatewayResult(Generic[T]):
    value: T | None
    shadow_verdict: AuthorizationVerdict | None = None
    enforced: bool = False


class GhostExecutionGateway:
    """Trusted computing base slice for high-consequence effects."""

    def __init__(self, *, mode: GhostShieldMode = GhostShieldMode.SHADOW) -> None:
        self.mode = mode
        self._engine = GhostShieldPolicyEngine()
        self._consumed_permits: set[str] = set()

    def authorize(
        self,
        action: CanonicalActionV1,
        ctx: AuthorizationContextV1,
    ):
        verdict = self._engine.evaluate(action, ctx)
        permit = None
        if verdict.verdict == AuthorizationVerdict.ALLOW:
            permit = self._engine.issue_permit(action, verdict)
        return verdict, permit

    def _pre_execute(
        self,
        *,
        action: CanonicalActionV1,
        ctx: AuthorizationContextV1,
        permit: ActionPermitV1 | None,
    ):
        """Shared TOCTOU re-validation for both sync and async effects.

        Returns (should_run_effect: bool, verdict) — callers run `effect()` themselves
        (or not, on DENY/LOCKDOWN) so this stays agnostic to sync vs. async effects.
        """
        verdict, fresh_permit = self.authorize(action, ctx)

        if self.mode == GhostShieldMode.DISABLED:
            return True, verdict, False

        if self.mode == GhostShieldMode.SHADOW:
            return True, verdict, False

        if self.mode == GhostShieldMode.LOCKDOWN:
            raise GatewayError("LOCKDOWN: protected effects blocked")

        # ENFORCE
        if verdict.verdict != AuthorizationVerdict.ALLOW:
            raise GatewayError(f"ENFORCE DENY: {verdict.reason_codes} — {verdict.human_explanation}")

        if permit is None or fresh_permit is None:
            raise GatewayError("ENFORCE requires valid permit")

        if permit.action_digest != action.canonical_digest():
            raise GatewayError("permit/action digest mismatch (mutation)")

        if permit.state_revision != ctx.runtime_revision:
            raise GatewayError("STATE_STALE at execution gateway")

        if permit.action_digest != fresh_permit.action_digest:
            raise GatewayError("permit replay or mutation detected")

        exp = permit.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise GatewayError("permit expired")

        pid = str(permit.permit_id)
        if permit.single_use:
            if pid in self._consumed_permits:
                raise GatewayError("permit already consumed (replay)")
            self._consumed_permits.add(pid)

        return True, verdict, True

    def execute_protected(
        self,
        *,
        action: CanonicalActionV1,
        ctx: AuthorizationContextV1,
        permit: ActionPermitV1 | None,
        effect: Callable[[], T],
    ) -> GatewayResult[T]:
        """Re-validate state at execution time (TOCTOU). Synchronous effects only."""
        _, verdict, enforced = self._pre_execute(action=action, ctx=ctx, permit=permit)
        result = effect()
        shadow = verdict.verdict if not enforced else AuthorizationVerdict.ALLOW
        return GatewayResult(value=result, shadow_verdict=shadow, enforced=enforced)

    async def execute_protected_async(
        self,
        *,
        action: CanonicalActionV1,
        ctx: AuthorizationContextV1,
        permit: ActionPermitV1 | None,
        effect: Callable[[], Awaitable[T]],
    ) -> GatewayResult[T]:
        """Async twin of `execute_protected` — same TOCTOU/permit checks, awaited effect.

        Needed for effects that are inherently async I/O (e.g. Vultr Serverless
        Inference HTTP calls) where the sync `execute_protected` cannot be used without
        blocking the event loop or losing concurrency.
        """
        _, verdict, enforced = self._pre_execute(action=action, ctx=ctx, permit=permit)
        result = await effect()
        shadow = verdict.verdict if not enforced else AuthorizationVerdict.ALLOW
        return GatewayResult(value=result, shadow_verdict=shadow, enforced=enforced)
