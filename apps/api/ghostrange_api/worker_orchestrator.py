"""Real worker E2E: provision → register → lease → execute → evidence → teardown."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict
from typing import Any

from .artifact_registry import ArtifactRegistry
from .cloud_init import worker_cloud_init
from .compute_provider import ComputeProvider, MockComputeProvider, WorkerHandle
from .config import Settings
from .netbird_gate import ensure_worker_mesh_ready, revoke_worker_peer
from .worker_models import WorkerLifecycle
from .worker_store import WorkerStore
from ghostrange_netbird_control import NetBirdClient


class RealWorkerOrchestrator:
    def __init__(
        self,
        settings: Settings,
        store: WorkerStore,
        provider: ComputeProvider,
        artifacts: ArtifactRegistry | None,
        netbird_client: NetBirdClient | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._provider = provider
        self._artifacts = artifacts
        self._netbird_client = netbird_client

    async def run_cpu_benchmark_test(
        self,
        *,
        range_id: uuid.UUID,
        live: bool,
        experiment_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        if self._settings.workers_live_only:
            live = True
        if live and (not self._settings.scheduler_live or not self._settings.vultr_api_key):
            raise RuntimeError("live worker test requires GHOSTSCHEDULER_LIVE and VULTR_API_KEY")
        if live and not self._settings.vultr_worker_vpc_id:
            raise RuntimeError("GHOSTRANGE_WORKER_VPC_ID required for live workers")
        run_id = uuid.uuid4()
        worker_id = uuid.uuid4()
        provider_name = "vultr" if live else "mock"
        provider: ComputeProvider = self._provider if live else self._provider
        if not live:
            from .compute_provider import MockComputeProvider

            provider = MockComputeProvider()
        await self._store.create_run(
            run_id=run_id, range_id=range_id, provider=provider_name, experiment_id=experiment_id
        )
        bootstrap = await self._store.issue_bootstrap(
            run_id=run_id,
            range_id=range_id,
            worker_id=worker_id,
            provider=provider_name,
            ttl_minutes=min(15, self._settings.max_worker_lifetime_minutes),
        )
        await self._store.create_task_for_run(run_id=run_id, range_id=range_id)
        public_url = self._settings.public_control_url
        local_url = self._settings.local_control_url
        user_data = None
        peer_hostname = f"gr-worker-{str(worker_id)[:8]}"
        if live:
            user_data = worker_cloud_init(
                control_url=public_url,
                bootstrap_token=bootstrap,
                netbird_setup_key=(
                    self._settings.netbird_worker_setup_key if self._settings.netbird_enabled else None
                ),
                netbird_peer_hostname=peer_hostname if self._settings.netbird_enabled else None,
            )

        handle: WorkerHandle | None = None
        try:
            if not live:
                asyncio.create_task(self._mock_worker_agent(local_url, bootstrap))

            # Compute-provider calls are synchronous HTTP/polling operations.
            # Keep them off the event loop: a live worker must be able to call
            # /v1/workers/register while Vultr's readiness poll is in flight.
            handle = await asyncio.to_thread(
                provider.create_worker,
                range_id=range_id,
                experiment_id=experiment_id,
                worker_id=worker_id,
                run_id=run_id,
                user_data=user_data,
            )
            await self._store.attach_provider_id(worker_id, handle.provider_compute_id, provider_name)
            await self._store.set_run_status(run_id, WorkerLifecycle.PROVISIONING.value)
            handle = await asyncio.to_thread(provider.wait_ready, handle, timeout_s=300.0)

            await self._store.wait_worker_registered(worker_id, timeout_s=480.0)  # cloud-init apt update + pip on a 1-CPU VM routinely exceeds 120s
            if live:
                await ensure_worker_mesh_ready(
                    settings=self._settings,
                    store=self._store,
                    client=self._netbird_client,
                    worker_id=worker_id,
                    peer_hostname=peer_hostname,
                )
            task = await self._store.wait_task_completed(run_id, timeout_s=180.0)
            backlog_count = await self._store.count_open_tasks(run_id)
            if backlog_count:
                raise RuntimeError(f"worker run {run_id} left {backlog_count} open tasks")
            worker = await self._store.get_worker(worker_id)
            run = await self._store.get_run(run_id)
            payload = task.get("payload") or {}
            if isinstance(payload, str):
                import json

                payload = json.loads(payload)
            bench = payload.get("result", {}) if isinstance(payload, dict) else {}
            artifact_id = task.get("artifact_id")
            return {
                "run_id": str(run_id),
                "worker_id": str(worker_id),
                "range_id": str(range_id),
                "experiment_id": str(experiment_id) if experiment_id else None,
                "live": live,
                "task_id": str(task["task_id"]),
                "provider_instance_id": handle.provider_compute_id if handle else None,
                "worker": {
                    "provider": handle.provider if handle else provider_name,
                    "provider_compute_id": handle.provider_compute_id if handle else None,
                    "main_ip": handle.main_ip if handle else None,
                    "plan": handle.plan if handle else None,
                },
                "benchmark": {
                    "score": float(bench.get("accumulator", bench.get("digest", 0)) or 0),
                    "duration_ms": int(bench.get("duration_ms", 0)),
                    "notes": "worker-runtime-cpu-benchmark",
                    "detail": bench,
                },
                "evidence_artifact_id": str(artifact_id) if artifact_id else None,
                "worker_status": worker["status"] if worker else None,
                "run_status": run["status"] if run else None,
                "task_completed": True,
                "backlog_count": backlog_count,
            }
        finally:
            # Reconcile task rows before infrastructure teardown. This closes the
            # failure window where a VM dies after task creation but before lease or
            # completion, so every run exits with zero pending work.
            await self._store.fail_open_tasks_for_run(
                run_id,
                reason="worker orchestrator teardown",
            )
            if handle is not None:
                await self._store.set_run_status(run_id, WorkerLifecycle.TERMINATING.value)
                # terminate_worker() -> destroy_compute() already confirms deletion via a
                # direct per-resource GET-poll before returning. Vultr's account-wide LIST
                # endpoint lags that by up to ~1-2 minutes (observed), so re-deriving success
                # from list_all_ghostrange_workers() below is racy against the very instance
                # we just authoritatively confirmed gone. Exclude it explicitly rather than
                # trusting the stale list for it.
                try:
                    await asyncio.to_thread(provider.terminate_worker, handle)
                finally:
                    if live:
                        revoke_worker_peer(self._settings, self._netbird_client, peer_hostname)
            await self._store.set_run_status(run_id, WorkerLifecycle.TERMINATED.value)
            await self._store.mark_worker_terminated(worker_id)
            # Real bug fixed here 2026-09-27: this used to fail if ANY worker
            # anywhere in the account was still present (after excluding this
            # one), not just whether THIS worker's own teardown succeeded.
            # With unrelated pre-existing orphans in the account (a separate,
            # real problem tracked by the orphan-reaper), every otherwise-
            # successful worker lifecycle would report "teardown incomplete"
            # for itself even though its own VM was genuinely gone. Check
            # membership of this worker's own id only - the account-wide
            # orphan count is a campaign/fan-out-level concern (see
            # live_worker_fanout.py's caller), not something that should turn
            # an individual successful worker into a reported failure.
            if handle is not None:
                owned_ids = {
                    w.provider_compute_id
                    for w in await asyncio.to_thread(provider.list_all_ghostrange_workers)
                }
                if handle.provider_compute_id in owned_ids:
                    raise RuntimeError(
                        f"teardown incomplete: worker {handle.provider_compute_id} still owned"
                    )

    async def _mock_worker_agent(self, control_url: str, bootstrap_token: str) -> None:
        from ghostrange_worker.runtime import WorkerRuntime

        def _run() -> None:
            WorkerRuntime(control_url, bootstrap_token).run_until_idle()

        await asyncio.to_thread(_run)
