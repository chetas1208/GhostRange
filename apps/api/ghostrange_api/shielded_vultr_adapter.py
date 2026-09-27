"""Shield range-runtime's ``VultrAdaptedComputeProvider`` through GhostExecutionGateway.

M17 bypass (see docs/security/GHOSTSHIELD_BYPASS_ANALYSIS.md): before this
module existed, ``orchestrator.py`` built
``VultrAdaptedComputeProvider`` directly around the live Vultr control
client and called ``start_provisioning`` / ``start_destroy`` on it. Those
calls perform the
actual billable ``create_world`` / ``create_compute`` / ``destroy_compute`` /
``destroy_world`` Vultr API effects, and they ran completely unmediated —
GHOSTSHIELD_MODE had no effect on this path at all, unlike the
``create_worker`` / ``terminate_worker`` port in ``compute_provider.py``,
which ``ShieldedComputeProvider`` already gates.

This wrapper puts the same
``Proposer -> GhostShield -> Permit -> GhostExecutionGateway -> Provider``
path in front of this second, structurally-different provider port (it uses
``start_provisioning`` / ``get_state`` / ``start_destroy`` at Range/World
granularity rather than ``create_worker`` / ``terminate_worker``), mapping
its effects onto the existing ``CREATE_WORLD`` / ``DESTROY_WORLD`` canonical
actions.

Fail-closed: ``GhostExecutionGateway.execute_protected`` only invokes the
wrapped ``effect`` callable (the real inner ``start_provisioning`` /
``start_destroy`` call) after a fresh ALLOW verdict + valid permit in
ENFORCE mode; DENY / STATE_STALE / permit mismatch / LOCKDOWN all raise
``GatewayError`` instead, and the real Vultr call never happens. There is no
except-and-continue anywhere in this module — a raised ``GatewayError``
propagates to the caller unmediated, and there is no fallback path that
calls the inner adapter directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from ghostrange_contracts._base import Id
from ghostrange_contracts.ghostshield_m17 import (
    AuthorizationContextV1,
    CanonicalActionType,
    CanonicalActionV1,
    GhostShieldMode,
)
from ghostrange_contracts.range import RangeSpecV1
from ghostrange_ghostshield import GhostExecutionGateway

if TYPE_CHECKING:
    from .config import Settings


class RangeWorldProvider(Protocol):
    """Structural shape of ``ghostrange_range_runtime.vultr_adapter.VultrAdaptedComputeProvider``."""

    def start_provisioning(
        self, *, range_id: Id, world_id: Id, spec: RangeSpecV1, correlation_id: str
    ) -> None: ...

    def get_state(self, *, range_id: Id, world_id: Id) -> Any: ...

    def start_destroy(self, *, range_id: Id, world_id: Id, correlation_id: str) -> None: ...


class ShieldedVultrAdapter:
    """Mediates billable world/compute effects; inner adapter is never called on DENY."""

    def __init__(
        self,
        inner: RangeWorldProvider,
        settings: "Settings",
        gateway: GhostExecutionGateway | None = None,
    ) -> None:
        self._inner = inner
        self._settings = settings
        self._gateway = gateway or GhostExecutionGateway(mode=GhostShieldMode.SHADOW)
        self._runtime_revision = 1
        self._provisioned: set[tuple[str, str]] = set()

    def _key(self, range_id: Id, world_id: Id) -> tuple[str, str]:
        return (str(range_id), str(world_id))

    def start_provisioning(
        self, *, range_id: Id, world_id: Id, spec: RangeSpecV1, correlation_id: str
    ) -> None:
        key = self._key(range_id, world_id)
        ctx = AuthorizationContextV1(
            campaign_id=range_id,
            runtime_revision=self._runtime_revision,
            active_workers=len(self._provisioned),
            max_active_workers=self._settings.max_active_worlds,
            budget_spent_usd=0.0,
            budget_hard_cap_usd=self._settings.max_campaign_cost_usd,
            safe_mode=False,
            allow_live_gpu=False,
            resource_owned=True,
        )
        action = CanonicalActionV1(
            action_type=CanonicalActionType.CREATE_WORLD,
            principal="range-runtime",
            campaign_id=range_id,
            target=str(world_id),
            parameters={"asset_count": len(spec.assets)},
            state_revision=ctx.runtime_revision,
            idempotency_key=f"create-world-{correlation_id}",
        )
        verdict, permit = self._gateway.authorize(action, ctx)

        def _effect() -> None:
            self._inner.start_provisioning(
                range_id=range_id, world_id=world_id, spec=spec, correlation_id=correlation_id
            )

        # GatewayError (DENY / LOCKDOWN / STATE_STALE / permit issues) raises
        # here and _effect is never invoked — no fallback to direct access.
        self._gateway.execute_protected(action=action, ctx=ctx, permit=permit, effect=_effect)
        self._provisioned.add(key)
        self._runtime_revision += 1

    def get_state(self, *, range_id: Id, world_id: Id) -> Any:
        # Read-only observation — not a protected effect, no gateway mediation needed.
        return self._inner.get_state(range_id=range_id, world_id=world_id)

    def start_destroy(self, *, range_id: Id, world_id: Id, correlation_id: str) -> None:
        key = self._key(range_id, world_id)
        resource_owned = key in self._provisioned
        ctx = AuthorizationContextV1(
            campaign_id=range_id,
            runtime_revision=self._runtime_revision,
            active_workers=len(self._provisioned),
            max_active_workers=self._settings.max_active_worlds,
            budget_spent_usd=0.0,
            budget_hard_cap_usd=self._settings.max_campaign_cost_usd,
            safe_mode=False,
            allow_live_gpu=False,
            resource_owned=resource_owned,
        )
        action = CanonicalActionV1(
            action_type=CanonicalActionType.DESTROY_WORLD,
            principal="range-runtime",
            campaign_id=range_id,
            target=str(world_id),
            parameters={},
            state_revision=ctx.runtime_revision,
            idempotency_key=f"destroy-world-{correlation_id}",
        )
        verdict, permit = self._gateway.authorize(action, ctx)

        def _effect() -> None:
            self._inner.start_destroy(range_id=range_id, world_id=world_id, correlation_id=correlation_id)

        self._gateway.execute_protected(action=action, ctx=ctx, permit=permit, effect=_effect)
        self._provisioned.discard(key)
        self._runtime_revision += 1


__all__ = ["ShieldedVultrAdapter", "RangeWorldProvider"]
