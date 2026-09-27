"""Postgres-backed worker/task/lease state (control plane only)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .worker_auth import hash_token, new_token
from .worker_models import WorkerLifecycle, WorkerTaskType


class WorkerStore:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create_run(
        self,
        *,
        run_id: uuid.UUID,
        range_id: uuid.UUID,
        provider: str,
        experiment_id: uuid.UUID | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO scheduler_worker_runs (
                        run_id, range_id, experiment_id, provider, status, created_at, metadata
                    ) VALUES (%(run_id)s, %(range_id)s, %(experiment_id)s, %(provider)s,
                              %(status)s, %(now)s, '{}'::jsonb)
                    """,
                    {
                        "run_id": run_id,
                        "range_id": range_id,
                        "experiment_id": experiment_id,
                        "provider": provider,
                        "status": WorkerLifecycle.REQUESTED.value,
                        "now": now,
                    },
                )

    async def issue_bootstrap(
        self,
        *,
        run_id: uuid.UUID,
        range_id: uuid.UUID,
        worker_id: uuid.UUID,
        provider: str = "mock",
        ttl_minutes: int = 15,
    ) -> str:
        token = new_token()
        exp = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO worker_bootstrap_tokens (token_hash, run_id, worker_id, range_id, expires_at)
                        VALUES (%(h)s, %(run_id)s, %(worker_id)s, %(range_id)s, %(exp)s)
                        """,
                        {
                            "h": hash_token(token),
                            "run_id": run_id,
                            "worker_id": worker_id,
                            "range_id": range_id,
                            "exp": exp,
                        },
                    )
                    await cur.execute(
                        """
                        INSERT INTO worker_instances (
                            worker_id, run_id, range_id, provider, status, expires_at
                        ) VALUES (%(worker_id)s, %(run_id)s, %(range_id)s, %(provider)s, %(status)s, %(exp)s)
                        """,
                        {
                            "worker_id": worker_id,
                            "run_id": run_id,
                            "range_id": range_id,
                            "provider": provider,
                            "status": WorkerLifecycle.PROVISIONING.value,
                            "exp": exp,
                        },
                    )
        return token

    async def register_worker(
        self, *, bootstrap_token: str, provider_instance_id: str | None, capabilities: dict[str, Any]
    ) -> tuple[uuid.UUID, str]:
        now = datetime.now(timezone.utc)
        worker_token = new_token()
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        SELECT worker_id, run_id, range_id, expires_at, consumed_at
                        FROM worker_bootstrap_tokens WHERE token_hash = %(h)s FOR UPDATE
                        """,
                        {"h": hash_token(bootstrap_token)},
                    )
                    row = await cur.fetchone()
                    if not row or row["consumed_at"] is not None:
                        raise PermissionError("invalid bootstrap token")
                    if row["expires_at"] < now:
                        raise PermissionError("bootstrap token expired")
                    await cur.execute(
                        """
                        UPDATE worker_bootstrap_tokens SET consumed_at = %(now)s WHERE token_hash = %(h)s
                        """,
                        {"now": now, "h": hash_token(bootstrap_token)},
                    )
                    worker_id = row["worker_id"]
                    await cur.execute(
                        """
                        UPDATE worker_instances
                        SET status = %(status)s,
                            worker_token_hash = %(tok)s,
                            provider_instance_id = COALESCE(%(pid)s, provider_instance_id),
                            capabilities = %(cap)s::jsonb,
                            ready_at = %(now)s,
                            last_seen_at = %(now)s
                        WHERE worker_id = %(wid)s
                        """,
                        {
                            "status": WorkerLifecycle.READY.value,
                            "tok": hash_token(worker_token),
                            "pid": provider_instance_id,
                            "cap": json.dumps(capabilities),
                            "now": now,
                            "wid": worker_id,
                        },
                    )
                    await cur.execute(
                        "UPDATE scheduler_worker_runs SET status = %(s)s WHERE run_id = %(rid)s",
                        {"s": WorkerLifecycle.READY.value, "rid": row["run_id"]},
                    )
        return worker_id, worker_token

    async def worker_from_token(self, worker_id: uuid.UUID, bearer: str) -> dict[str, Any]:
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM worker_instances WHERE worker_id = %(id)s",
                    {"id": worker_id},
                )
                row = await cur.fetchone()
        if not row or row["worker_token_hash"] != hash_token(bearer):
            raise PermissionError("invalid worker token")
        return dict(row)

    async def heartbeat(self, worker_id: uuid.UUID, *, status: str, task_id: str | None) -> None:
        now = datetime.now(timezone.utc)
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE worker_instances
                    SET last_seen_at = %(now)s,
                        status = CASE WHEN %(status)s = 'RUNNING' THEN 'RUNNING' ELSE status END,
                        metadata = metadata || %(meta)s::jsonb
                    WHERE worker_id = %(wid)s
                    """,
                    {
                        "now": now,
                        "status": status,
                        "meta": json.dumps({"current_task_id": task_id}),
                        "wid": worker_id,
                    },
                )

    async def create_task_for_run(self, *, run_id: uuid.UUID, range_id: uuid.UUID) -> uuid.UUID:
        task_id = uuid.uuid4()
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO worker_tasks (
                        task_id, run_id, range_id, task_type, status, payload
                    ) VALUES (%(tid)s, %(run_id)s, %(range_id)s, %(type)s, 'PENDING', '{}'::jsonb)
                    """,
                    {
                        "tid": task_id,
                        "run_id": run_id,
                        "range_id": range_id,
                        "type": WorkerTaskType.CPU_BENCHMARK.value,
                    },
                )
        return task_id

    async def lease_next_task(self, worker_id: uuid.UUID, *, lease_seconds: int = 180) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=lease_seconds)
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "SELECT run_id, range_id, status FROM worker_instances WHERE worker_id = %(w)s FOR UPDATE",
                        {"w": worker_id},
                    )
                    worker = await cur.fetchone()
                    if not worker or worker["status"] not in (
                        WorkerLifecycle.READY.value,
                        WorkerLifecycle.REGISTERING.value,
                    ):
                        return None
                    await cur.execute(
                        """
                        SELECT task_id, run_id, range_id, task_type, payload
                        FROM worker_tasks
                        WHERE run_id = %(run)s AND status = 'PENDING'
                        ORDER BY created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                        """,
                        {"run": worker["run_id"]},
                    )
                    task = await cur.fetchone()
                    if not task:
                        return None
                    lease_id = uuid.uuid4()
                    await cur.execute(
                        """
                        INSERT INTO worker_leases (lease_id, task_id, worker_id, status, expires_at)
                        VALUES (%(lid)s, %(tid)s, %(wid)s, 'ACTIVE', %(exp)s)
                        """,
                        {"lid": lease_id, "tid": task["task_id"], "wid": worker_id, "exp": exp},
                    )
                    await cur.execute(
                        """
                        UPDATE worker_tasks
                        SET status = 'LEASED', worker_id = %(wid)s, started_at = %(now)s
                        WHERE task_id = %(tid)s
                        """,
                        {"wid": worker_id, "now": now, "tid": task["task_id"]},
                    )
                    await cur.execute(
                        "UPDATE worker_instances SET status = %(s)s WHERE worker_id = %(wid)s",
                        {"s": WorkerLifecycle.LEASED.value, "wid": worker_id},
                    )
        return {
            "lease_id": str(lease_id),
            "task_id": str(task["task_id"]),
            "task_type": task["task_type"],
            "payload": task["payload"],
        }

    async def complete_task(
        self,
        worker_id: uuid.UUID,
        task_id: uuid.UUID,
        *,
        result: dict[str, Any],
        artifact_id: uuid.UUID | None,
    ) -> None:
        now = datetime.now(timezone.utc)
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE worker_tasks
                        SET status = 'COMPLETED', completed_at = %(now)s, artifact_id = %(aid)s,
                            payload = payload || %(res)s::jsonb
                        WHERE task_id = %(tid)s AND worker_id = %(wid)s
                        """,
                        {
                            "now": now,
                            "aid": artifact_id,
                            "res": json.dumps({"result": result}),
                            "tid": task_id,
                            "wid": worker_id,
                        },
                    )
                    await cur.execute(
                        """
                        UPDATE worker_instances SET status = %(s)s WHERE worker_id = %(wid)s
                        """,
                        {"s": WorkerLifecycle.COMPLETED.value, "wid": worker_id},
                    )
                    await cur.execute(
                        """
                        UPDATE worker_leases SET status = 'RELEASED' WHERE task_id = %(tid)s
                        """,
                        {"tid": task_id},
                    )

    async def fail_task(self, worker_id: uuid.UUID, task_id: uuid.UUID, reason: str) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE worker_tasks SET status = 'FAILED', failure_reason = %(r)s
                        WHERE task_id = %(tid)s AND worker_id = %(wid)s
                        """,
                        {"r": reason, "tid": task_id, "wid": worker_id},
                    )
                    await cur.execute(
                        """
                        UPDATE worker_leases SET status = 'RELEASED'
                        WHERE task_id = %(tid)s AND worker_id = %(wid)s AND status = 'ACTIVE'
                        """,
                        {"tid": task_id, "wid": worker_id},
                    )
                    await cur.execute(
                        "UPDATE worker_instances SET status = %(s)s, failure_reason = %(r)s WHERE worker_id = %(wid)s",
                        {"s": WorkerLifecycle.TASK_FAILED.value, "r": reason, "wid": worker_id},
                    )

    async def fail_open_tasks_for_run(self, run_id: uuid.UUID, *, reason: str) -> int:
        """Close every non-terminal task before a worker run is torn down.

        A provisioning or network failure can happen after the task row is inserted but
        before the worker leases it. Leaving that row ``PENDING`` creates a durable
        backlog that can be picked up by a later worker or make health checks report a
        false active run. Teardown owns this reconciliation step, and the transaction
        releases any associated leases before marking the task failed.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM worker_tasks
                        WHERE run_id = %(run_id)s
                          AND status NOT IN ('COMPLETED', 'FAILED', 'CANCELLED')
                        """,
                        {"run_id": run_id},
                    )
                    row = await cur.fetchone()
                    open_count = int(row[0]) if row else 0
                    if open_count == 0:
                        return 0
                    await cur.execute(
                        """
                        UPDATE worker_leases
                        SET status = 'RELEASED'
                        WHERE task_id IN (
                            SELECT task_id FROM worker_tasks
                            WHERE run_id = %(run_id)s
                              AND status NOT IN ('COMPLETED', 'FAILED', 'CANCELLED')
                        )
                          AND status = 'ACTIVE'
                        """,
                        {"run_id": run_id},
                    )
                    await cur.execute(
                        """
                        UPDATE worker_tasks
                        SET status = 'FAILED', failure_reason = %(reason)s
                        WHERE run_id = %(run_id)s
                          AND status NOT IN ('COMPLETED', 'FAILED', 'CANCELLED')
                        """,
                        {"run_id": run_id, "reason": reason},
                    )
        return open_count

    async def count_open_tasks(self, run_id: uuid.UUID) -> int:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM worker_tasks
                    WHERE run_id = %(run_id)s
                      AND status NOT IN ('COMPLETED', 'FAILED', 'CANCELLED')
                    """,
                    {"run_id": run_id},
                )
                row = await cur.fetchone()
        return int(row[0]) if row else 0

    # Terminal states for the records a lease can safely be reconciled
    # against — see release_stale_lease().
    _TERMINAL_TASK_STATUSES = frozenset({"COMPLETED", "FAILED"})
    _TERMINAL_WORKER_STATUSES = frozenset(
        {
            WorkerLifecycle.COMPLETED.value,
            WorkerLifecycle.TERMINATED.value,
            WorkerLifecycle.TASK_FAILED.value,
            WorkerLifecycle.BOOT_FAILED.value,
            WorkerLifecycle.REGISTRATION_FAILED.value,
            WorkerLifecycle.BOOTSTRAP_FAILED.value,
            WorkerLifecycle.ORPHANED.value,
        }
    )
    _TERMINAL_RUN_STATUSES = _TERMINAL_WORKER_STATUSES

    async def release_stale_lease(self, lease_id: uuid.UUID) -> str:
        """Reconciliation primitive: mark one expired lease RELEASED, but
        only after independently re-verifying — inside this transaction,
        against current DB state — that it is actually safe to touch.

        This never trusts a caller's claim that a lease is dead. It
        refuses (raises ``ValueError``) unless, right now, in the DB:
          - the lease exists and is still ``ACTIVE`` (idempotent no-op if
            already ``RELEASED``),
          - ``expires_at`` is in the past, and
          - the lease's task, worker, and run are all in a terminal state.

        Returns one of "released" / "already_released" for observability;
        never silently no-ops on something that turned out not to be dead.
        """
        now = datetime.now(timezone.utc)
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        SELECT l.status AS lease_status, l.expires_at,
                               t.status AS task_status,
                               w.status AS worker_status,
                               r.status AS run_status
                        FROM worker_leases l
                        JOIN worker_tasks t ON t.task_id = l.task_id
                        JOIN worker_instances w ON w.worker_id = l.worker_id
                        JOIN scheduler_worker_runs r ON r.run_id = t.run_id
                        WHERE l.lease_id = %(lid)s
                        FOR UPDATE OF l
                        """,
                        {"lid": lease_id},
                    )
                    row = await cur.fetchone()
                    if row is None:
                        raise ValueError(f"lease {lease_id} does not exist")
                    if row["lease_status"] == "RELEASED":
                        return "already_released"
                    if row["lease_status"] != "ACTIVE":
                        raise ValueError(
                            f"lease {lease_id} has status {row['lease_status']!r}; "
                            "only ACTIVE leases are eligible for reconciliation"
                        )
                    if row["expires_at"] >= now:
                        raise ValueError(f"lease {lease_id} has not expired yet ({row['expires_at']}); refusing to release")
                    if row["task_status"] not in self._TERMINAL_TASK_STATUSES:
                        raise ValueError(f"lease {lease_id}: task status {row['task_status']!r} is not terminal; refusing")
                    if row["worker_status"] not in self._TERMINAL_WORKER_STATUSES:
                        raise ValueError(f"lease {lease_id}: worker status {row['worker_status']!r} is not terminal; refusing")
                    if row["run_status"] not in self._TERMINAL_RUN_STATUSES:
                        raise ValueError(f"lease {lease_id}: run status {row['run_status']!r} is not terminal; refusing")

                    await cur.execute(
                        "UPDATE worker_leases SET status = 'RELEASED' WHERE lease_id = %(lid)s",
                        {"lid": lease_id},
                    )
        return "released"

    async def mark_worker_bootstrap_failed(self, worker_id: uuid.UUID, *, reason: str) -> None:
        """NetBird enrollment (peer connected + in NETBIRD_WORKER_GROUP) did
        not complete within the readiness-gate timeout. Mirrors fail_task's
        pattern: record the reason and set a terminal-ish failure status;
        the caller is still expected to actually terminate the underlying
        Vultr VM (this method only records state, it does not tear down
        infrastructure)."""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE worker_instances SET status = %(s)s, failure_reason = %(r)s WHERE worker_id = %(wid)s
                    """,
                    {"s": WorkerLifecycle.BOOTSTRAP_FAILED.value, "r": reason, "wid": worker_id},
                )

    async def mark_worker_terminated(self, worker_id: uuid.UUID) -> None:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE worker_instances
                    SET status = %(s)s, terminated_at = now()
                    WHERE worker_id = %(wid)s
                    """,
                    {"s": WorkerLifecycle.TERMINATED.value, "wid": worker_id},
                )

    async def drain_worker(self, worker_id: uuid.UUID) -> None:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE worker_instances SET status = %(s)s WHERE worker_id = %(wid)s",
                    {"s": WorkerLifecycle.DRAINING.value, "wid": worker_id},
                )

    async def wait_worker_registered(
        self, worker_id: uuid.UUID, *, timeout_s: float = 300.0, poll_s: float = 2.0
    ) -> dict[str, Any]:
        import asyncio

        deadline = asyncio.get_running_loop().time() + timeout_s
        while asyncio.get_running_loop().time() < deadline:
            row = await self.get_worker(worker_id)
            if row and row.get("worker_token_hash"):
                return row
            await asyncio.sleep(poll_s)
        raise TimeoutError(f"worker {worker_id} not registered within {timeout_s}s")

    async def wait_worker_status(
        self, worker_id: uuid.UUID, want: str, *, timeout_s: float = 300.0, poll_s: float = 2.0
    ) -> dict[str, Any]:
        import asyncio

        deadline = asyncio.get_running_loop().time() + timeout_s
        while asyncio.get_running_loop().time() < deadline:
            row = await self.get_worker(worker_id)
            if row and row["status"] == want:
                return row
            await asyncio.sleep(poll_s)
        raise TimeoutError(f"worker {worker_id} not {want} within {timeout_s}s")

    async def wait_task_completed(self, run_id: uuid.UUID, *, timeout_s: float = 300.0, poll_s: float = 2.0) -> dict[str, Any]:
        import asyncio

        deadline = asyncio.get_running_loop().time() + timeout_s
        while asyncio.get_running_loop().time() < deadline:
            task = await self.get_task_for_run(run_id)
            if task and task["status"] == "COMPLETED":
                return task
            if task and task["status"] == "FAILED":
                raise RuntimeError(task.get("failure_reason") or "task failed")
            await asyncio.sleep(poll_s)
        raise TimeoutError(f"run {run_id} task not completed within {timeout_s}s")

    async def get_task_for_run(self, run_id: uuid.UUID) -> dict[str, Any] | None:
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM worker_tasks WHERE run_id = %(run)s ORDER BY created_at ASC LIMIT 1",
                    {"run": run_id},
                )
                row = await cur.fetchone()
        return dict(row) if row else None

    async def get_worker(self, worker_id: uuid.UUID) -> dict[str, Any] | None:
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("SELECT * FROM worker_instances WHERE worker_id = %(id)s", {"id": worker_id})
                row = await cur.fetchone()
        return dict(row) if row else None

    async def get_run(self, run_id: uuid.UUID) -> dict[str, Any] | None:
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("SELECT * FROM scheduler_worker_runs WHERE run_id = %(id)s", {"id": run_id})
                row = await cur.fetchone()
        return dict(row) if row else None

    async def set_run_status(self, run_id: uuid.UUID, status: str, **fields: Any) -> None:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE scheduler_worker_runs SET status = %(s)s WHERE run_id = %(id)s",
                    {"s": status, "id": run_id},
                )

    async def attach_provider_id(self, worker_id: uuid.UUID, provider_instance_id: str, provider: str) -> None:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE worker_instances
                    SET provider_instance_id = %(pid)s, provider = %(prov)s,
                        status = %(status)s
                    WHERE worker_id = %(wid)s
                    """,
                    {
                        "pid": provider_instance_id,
                        "prov": provider,
                        "status": WorkerLifecycle.BOOTSTRAPPING.value,
                        "wid": worker_id,
                    },
                )
