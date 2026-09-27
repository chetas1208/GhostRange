"""GhostScheduler ephemeral worker jobs with hard budget gates."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from .artifact_registry import ArtifactRegistry
from .compute_provider import ComputeProvider
from .config import Settings
from .worker_orchestrator import RealWorkerOrchestrator


class BudgetExceededError(RuntimeError):
    pass


class WorkerScheduler:
    def __init__(
        self,
        settings: Settings,
        pool: AsyncConnectionPool,
        provider: ComputeProvider,
        artifacts: ArtifactRegistry | None,
        orchestrator: RealWorkerOrchestrator | None = None,
    ) -> None:
        self._settings = settings
        self._pool = pool
        self._provider = provider
        self._artifacts = artifacts
        self._orchestrator = orchestrator

    async def _active_worker_count(self) -> int:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*) FROM scheduler_worker_runs
                    WHERE status NOT IN ('TERMINATED', 'terminated', 'failed')
                      AND terminated_at IS NULL
                    """
                )
                row = await cur.fetchone()
        return int(row[0]) if row else 0

    async def _assert_budget(self, *, live: bool = False) -> None:
        # Real Vultr Compute VMs are billable infrastructure — use the dedicated compute
        # cap (default 1), never the inference-pool cap. Do not merge these two knobs.
        cap = self._settings.compute_worker_concurrency_cap
        active = await self._active_worker_count()
        if active >= cap:
            raise BudgetExceededError(
                f"MAX_ACTIVE_COMPUTE_WORKERS={cap} reached ({active} active)"
            )
        if live:
            owned = self._provider.list_all_ghostrange_workers()
            if len(owned) >= cap:
                raise BudgetExceededError(
                    f"provider reports {len(owned)} owned workers (max {cap})"
                )

    async def run_benchmark_job(
        self,
        *,
        range_id: uuid.UUID,
        experiment_id: uuid.UUID | None = None,
        live: bool = False,
    ) -> dict:
        await self._assert_budget(live=live)
        if self._orchestrator is None:
            raise RuntimeError("worker orchestrator unavailable (postgres required)")
        if live:
            if not self._settings.scheduler_live:
                raise RuntimeError("GHOSTSCHEDULER_LIVE must be true for live worker test")
            if not self._settings.vultr_api_key or not self._settings.vultr_worker_vpc_id:
                raise RuntimeError("VULTR_API_KEY and GHOSTRANGE_WORKER_VPC_ID required for live workers")
        result = await self._orchestrator.run_cpu_benchmark_test(
            range_id=range_id,
            live=live,
            experiment_id=experiment_id,
        )
        now = datetime.now(timezone.utc)
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE scheduler_worker_runs
                    SET status = 'terminated',
                        terminated_at = %(t)s,
                        provider_compute_id = %(cid)s,
                        benchmark_score = %(score)s,
                        metadata = metadata || %(meta)s::jsonb
                    WHERE run_id = %(run_id)s
                    """,
                    {
                        "run_id": uuid.UUID(result["run_id"]),
                        "t": now,
                        "cid": result.get("provider_instance_id"),
                        "score": result.get("benchmark", {}).get("score"),
                        "meta": Jsonb(
                            {
                                "worker_id": result.get("worker_id"),
                                "task_id": result.get("task_id"),
                                "evidence_artifact_id": result.get("evidence_artifact_id"),
                                "live": result.get("live"),
                            }
                        ),
                    },
                )
        return result

    async def list_runs(self, range_id: uuid.UUID) -> list[dict]:
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT run_id, range_id, experiment_id, provider, status, benchmark_score,
                           created_at, terminated_at, metadata
                    FROM scheduler_worker_runs
                    WHERE range_id = %(range_id)s
                    ORDER BY created_at DESC
                    LIMIT 50
                    """,
                    {"range_id": range_id},
                )
                rows = await cur.fetchall()
        return [dict(r) for r in rows]
