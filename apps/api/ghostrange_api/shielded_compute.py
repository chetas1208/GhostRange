"""Wrap ComputeProvider so create/terminate pass through GhostExecutionGateway."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from ghostrange_contracts.ghostshield_m17 import (
    AuthorizationContextV1,
    CanonicalActionType,
    CanonicalActionV1,
    GhostShieldMode,
)
from ghostrange_ghostshield import GhostExecutionGateway, GatewayError

from .compute_provider import ComputeProvider, WorkerHandle

if TYPE_CHECKING:
    from .config import Settings


class ShieldedComputeProvider:
    """Mediates billable worker effects; inner provider never called on ENFORCE DENY."""

    def __init__(
        self,
        inner: ComputeProvider,
        settings: Settings,
        gateway: GhostExecutionGateway | None = None,
    ) -> None:
        self._inner = inner
        self._settings = settings
        self._gateway = gateway or GhostExecutionGateway(mode=GhostShieldMode.SHADOW)
        self._runtime_revision = 1
        self._worker_campaign: dict[str, uuid.UUID] = {}

    def verify_api(self) -> None:
        if hasattr(self._inner, "verify_api"):
            self._inner.verify_api()  # type: ignore[attr-defined]

    def list_all_ghostrange_workers(self) -> list[WorkerHandle]:
        if hasattr(self._inner, "list_all_ghostrange_workers"):
            return self._inner.list_all_ghostrange_workers()  # type: ignore[attr-defined]
        return self._inner.list_owned_workers(range_id=None)

    def _auth_ctx(self, range_id: uuid.UUID, *, resource_owned: bool = True) -> AuthorizationContextV1:
        active = len(self._inner.list_owned_workers(range_id=range_id))
        return AuthorizationContextV1(
            campaign_id=range_id,
            runtime_revision=self._runtime_revision,
            active_workers=active,
            # Real billable Vultr Compute VMs — dedicated cap, never the inference-pool cap.
            max_active_workers=self._settings.compute_worker_concurrency_cap,
            budget_spent_usd=0.0,
            budget_hard_cap_usd=self._settings.max_campaign_cost_usd,
            safe_mode=False,
            allow_live_gpu=False,
            resource_owned=resource_owned,
        )

    def create_worker(
        self,
        *,
        range_id: uuid.UUID,
        experiment_id: uuid.UUID | None,
        worker_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        user_data: str | None = None,
    ) -> WorkerHandle:
        ctx = self._auth_ctx(range_id)
        action = CanonicalActionV1(
            action_type=CanonicalActionType.CREATE_WORKER,
            principal="ghostscheduler",
            campaign_id=range_id,
            target=str(worker_id or run_id or "worker"),
            parameters={
                "plan": self._settings.vultr_worker_plan,
                "region": self._settings.vultr_worker_region,
            },
            state_revision=ctx.runtime_revision,
            idempotency_key=str(run_id or worker_id or uuid.uuid4()),
        )
        verdict, permit = self._gateway.authorize(action, ctx)

        def _effect() -> WorkerHandle:
            return self._inner.create_worker(
                range_id=range_id,
                experiment_id=experiment_id,
                worker_id=worker_id,
                run_id=run_id,
                user_data=user_data,
            )

        try:
            result = self._gateway.execute_protected(
                action=action, ctx=self._auth_ctx(range_id), permit=permit, effect=_effect
            )
        except GatewayError:
            raise
        self._runtime_revision += 1
        assert result.value is not None
        self._worker_campaign[result.value.provider_compute_id] = range_id
        return result.value

    def wait_ready(self, handle: WorkerHandle, *, timeout_s: float = 300.0) -> WorkerHandle:
        return self._inner.wait_ready(handle, timeout_s=timeout_s)

    def run_benchmark(self, handle: WorkerHandle):
        return self._inner.run_benchmark(handle)

    def terminate_worker(self, handle: WorkerHandle) -> None:
        owned_ids = {h.provider_compute_id for h in self._inner.list_owned_workers(range_id=None)}
        resource_owned = handle.provider_compute_id in owned_ids
        range_id = self._worker_campaign.get(handle.provider_compute_id, uuid.UUID(int=0))
        ctx = self._auth_ctx(range_id, resource_owned=resource_owned)
        action = CanonicalActionV1(
            action_type=CanonicalActionType.TERMINATE_WORKER,
            principal="ghostscheduler",
            campaign_id=range_id,
            target=handle.provider_compute_id,
            parameters={},
            state_revision=ctx.runtime_revision,
            idempotency_key=f"term-{handle.provider_compute_id}",
        )
        verdict, permit = self._gateway.authorize(action, ctx)

        def _effect() -> None:
            self._inner.terminate_worker(handle)

        fresh = self._auth_ctx(range_id, resource_owned=resource_owned)
        self._gateway.execute_protected(
            action=action,
            ctx=fresh,
            permit=permit,
            effect=_effect,
        )
        self._runtime_revision += 1

    def list_owned_workers(self, *, range_id: uuid.UUID | None = None) -> list[WorkerHandle]:
        return self._inner.list_owned_workers(range_id=range_id)
