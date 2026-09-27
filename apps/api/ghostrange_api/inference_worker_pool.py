"""Real concurrent worker execution driven by Vultr Serverless Inference.

Distinct from the Vultr *Compute* worker pool in `worker_orchestrator.py`/`worker_scheduler.py`
(which provisions/terminates billable VMs and is gated behind GHOSTSCHEDULER_LIVE + a VPC).
This module treats each Vultr Serverless Inference chat-completion call as one "worker" unit
of investigation/scheduling work, and fans a batch of tasks out to up to
`MAX_ACTIVE_WORKERS` (hard-clamped to 10, see `Settings.inference_worker_concurrency_cap`)
concurrent real HTTP calls against `https://api.vultrinference.com/v1/chat/completions`.

Every dispatch is mediated by GhostExecutionGateway (same trusted-computing-base slice that
guards Vultr Compute worker create/terminate in `shielded_compute.py`), using a new
CanonicalActionType.INFERENCE_WORKER_CALL action so GHOSTSHIELD_MODE=ENFORCE actually blocks
over-cap/over-budget dispatch (raises GatewayError), not just logs a warning.

Two hard caps, enforced in-process (not just configured):
  - concurrency: asyncio.Semaphore(effective_max_workers) + a locked active-worker counter fed
    into the same AuthorizationContextV1.active_workers/max_active_workers the gateway's P2
    invariant ("never exceed MAX_ACTIVE_WORKERS") already checks for Compute workers.
  - budget: a locked cumulative-spend counter (session-scoped, resets per process) checked
    against `Settings.inference_worker_budget_cap_usd` (hard ceiling $25) both by this pool
    *before* incrementing active count, and by the policy engine's BUDGET_HARD_CAP /
    INFERENCE_SPEND_GUARD check inside the gateway — belt and suspenders.

Cost accounting caveat (documented, not hidden): Vultr's public docs describe Serverless
Inference as pay-per-token but do not publish an exact $/token rate we could find in
docs/research/VULTR.md. `_ESTIMATED_USD_PER_CALL` is a deliberately conservative flat
per-call estimate (worst case for a small instruct model at modest max_tokens) so the guard
fails closed (blocks slightly early) rather than open (never blocks). Swap in a real
$/token rate here once Vultr's billing API/console exposes one for this account.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ghostrange_contracts.ghostshield_m17 import (
    AuthorizationContextV1,
    CanonicalActionType,
    CanonicalActionV1,
)
from ghostrange_ghostshield import GatewayError, GhostExecutionGateway

from .config import Settings
from .inference_service import InferenceService

from .inference_costing import (
    micros_to_float_usd,
    reserve_usd_micros_for_call,
    actual_usd_micros_from_response,
)

# Pre-call reserve when usage unknown (fail-closed budget guard).
_ESTIMATED_USD_PER_CALL = micros_to_float_usd(reserve_usd_micros_for_call())


class InferenceWorkerBudgetExceeded(RuntimeError):
    pass


@dataclass
class InferenceWorkerTask:
    system: str
    user: str
    max_tokens: int = 256
    label: str = ""


@dataclass
class InferenceWorkerResult:
    request_id: str
    label: str
    ok: bool
    started_at: str
    finished_at: str
    duration_ms: int
    active_workers_at_dispatch: int
    error: str | None = None
    response: dict[str, Any] | None = None


@dataclass
class DispatchBatchResult:
    results: list[InferenceWorkerResult] = field(default_factory=list)
    requested: int = 0
    dispatched: int = 0
    refused: int = 0
    max_observed_concurrency: int = 0
    spent_usd: float = 0.0
    budget_cap_usd: float = 0.0
    concurrency_cap: int = 0
    ghostshield_mode: str = ""


class InferenceWorkerPool:
    """Dispatches a batch of tasks as real, concurrent Vultr Serverless Inference calls."""

    def __init__(
        self,
        settings: Settings,
        inference: InferenceService,
        gateway: GhostExecutionGateway,
        *,
        campaign_id: uuid.UUID | None = None,
    ) -> None:
        self._settings = settings
        self._inference = inference
        self._gateway = gateway
        self._campaign_id = campaign_id or uuid.UUID(int=0)

        self._max_workers = settings.inference_worker_concurrency_cap
        self._budget_cap = settings.inference_worker_budget_cap_usd
        self._sem = asyncio.Semaphore(self._max_workers)
        self._lock = asyncio.Lock()
        self._active = 0
        self._spent_usd = 0.0
        self._runtime_revision = 1
        self._concurrent_now = 0
        self._max_observed_concurrency = 0

    @property
    def available(self) -> bool:
        return self._inference.available

    def _auth_ctx(self, *, active_workers: int) -> AuthorizationContextV1:
        return AuthorizationContextV1(
            campaign_id=self._campaign_id,
            runtime_revision=self._runtime_revision,
            active_workers=active_workers,
            max_active_workers=self._max_workers,
            budget_spent_usd=self._spent_usd,
            budget_hard_cap_usd=self._budget_cap,
            safe_mode=False,
            allow_live_gpu=False,
            resource_owned=True,
        )

    async def dispatch_batch(self, tasks: list[InferenceWorkerTask]) -> DispatchBatchResult:
        if not self._inference.available:
            raise RuntimeError("inference not configured (VULTR_INFERENCE_API_KEY missing)")
        batch = DispatchBatchResult(
            requested=len(tasks),
            budget_cap_usd=self._budget_cap,
            concurrency_cap=self._max_workers,
            ghostshield_mode=self._gateway.mode.value,
        )
        coros = [self._dispatch_one(t, batch) for t in tasks]
        results = await asyncio.gather(*coros)
        batch.results = list(results)
        batch.dispatched = sum(1 for r in batch.results if r.ok)
        batch.refused = sum(1 for r in batch.results if not r.ok)
        batch.max_observed_concurrency = self._max_observed_concurrency
        batch.spent_usd = self._spent_usd
        return batch

    async def _dispatch_one(
        self, task: InferenceWorkerTask, batch: DispatchBatchResult
    ) -> InferenceWorkerResult:
        request_id = str(uuid.uuid4())
        async with self._sem:
            async with self._lock:
                # `preexisting_active` mirrors shielded_compute.py's semantics for
                # CREATE_WORKER: it's the count of *other* workers already active,
                # not including this dispatch — matches the gateway's P2 invariant
                # ("never exceed MAX_ACTIVE_WORKERS") which the M17 test suite exercises
                # as active_workers >= max_active_workers => DENY on the Nth *new* request.
                preexisting_active = self._active
                if self._spent_usd + _ESTIMATED_USD_PER_CALL > self._budget_cap:
                    return InferenceWorkerResult(
                        request_id=request_id,
                        label=task.label,
                        ok=False,
                        started_at=_now_iso(),
                        finished_at=_now_iso(),
                        duration_ms=0,
                        active_workers_at_dispatch=preexisting_active,
                        error=(
                            f"INFERENCE_WORKER_BUDGET_GUARD: spent={self._spent_usd:.4f} + "
                            f"est={_ESTIMATED_USD_PER_CALL:.4f} would exceed cap={self._budget_cap:.4f}"
                        ),
                    )
                if preexisting_active >= self._max_workers:
                    return InferenceWorkerResult(
                        request_id=request_id,
                        label=task.label,
                        ok=False,
                        started_at=_now_iso(),
                        finished_at=_now_iso(),
                        duration_ms=0,
                        active_workers_at_dispatch=preexisting_active,
                        error=(
                            f"INFERENCE_WORKER_CONCURRENCY_GUARD: active={preexisting_active} "
                            f">= max={self._max_workers}"
                        ),
                    )
                self._active += 1
                self._concurrent_now += 1
                self._max_observed_concurrency = max(
                    self._max_observed_concurrency, self._concurrent_now
                )
                active_at_dispatch = self._active

            action = CanonicalActionV1(
                action_type=CanonicalActionType.INFERENCE_WORKER_CALL,
                principal="ghostrange-inference-worker-pool",
                campaign_id=self._campaign_id,
                target=request_id,
                parameters={
                    "estimated_cost_usd": _ESTIMATED_USD_PER_CALL,
                    "model": self._settings.inference_model,
                    "label": task.label,
                },
                state_revision=self._runtime_revision,
                idempotency_key=request_id,
            )
            ctx = self._auth_ctx(active_workers=preexisting_active)
            verdict, permit = self._gateway.authorize(action, ctx)

            started = time.perf_counter()
            started_at = _now_iso()
            error: str | None = None
            response: dict[str, Any] | None = None
            ok = False
            try:

                async def _effect() -> dict[str, Any]:
                    return await self._inference.complete_json(
                        system=task.system, user=task.user, max_tokens=task.max_tokens
                    )

                gw_result = await self._gateway.execute_protected_async(
                    action=action, ctx=ctx, permit=permit, effect=_effect
                )
                response = gw_result.value
                ok = True
            except GatewayError as exc:
                error = f"GHOSTSHIELD_{self._gateway.mode.value}: {exc}"
            except Exception as exc:  # noqa: BLE001 — surface real HTTP/inference errors to caller
                error = f"{type(exc).__name__}: {exc}"
            finally:
                duration_ms = int((time.perf_counter() - started) * 1000)
                async with self._lock:
                    self._active -= 1
                    self._concurrent_now -= 1
                    self._runtime_revision += 1
                    if ok:
                        micros, _basis = actual_usd_micros_from_response(
                            self._settings.inference_model, response
                        )
                        self._spent_usd += micros_to_float_usd(micros)

            return InferenceWorkerResult(
                request_id=request_id,
                label=task.label,
                ok=ok,
                started_at=started_at,
                finished_at=_now_iso(),
                duration_ms=duration_ms,
                active_workers_at_dispatch=active_at_dispatch,
                error=error,
                response=response,
            )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
