"""WorkerStore.release_stale_lease: the safety-critical reconciliation
primitive behind apps/api/ghostrange_api/reconcile_leases.py.

Requires a real Postgres to exercise the actual multi-table transaction
(worker_leases JOIN worker_tasks JOIN worker_instances JOIN
scheduler_worker_runs) — same convention as test_worker_mock_e2e.py,
skipped when no DATABASE_URL/POSTGRES_DSN is configured for this test run.
This suite never touches production: it opens its own pool from the env
var and creates/deletes its own rows.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.skipif(
    not (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_DSN")),
    reason="DATABASE_URL or POSTGRES_DSN required",
)


@pytest.fixture
async def store():
    from psycopg_pool import AsyncConnectionPool

    from ghostrange_api.worker_store import WorkerStore

    dsn = os.environ.get("POSTGRES_DSN") or os.environ.get("DATABASE_URL")
    pool = AsyncConnectionPool(dsn, min_size=1, max_size=2, open=False)
    await pool.open(wait=True, timeout=30)
    yield WorkerStore(pool)
    await pool.close()


async def _seed(
    store,
    *,
    lease_status: str = "ACTIVE",
    expires_at: datetime,
    task_status: str = "COMPLETED",
    worker_status: str = "TERMINATED",
    run_status: str = "TERMINATED",
) -> uuid.UUID:
    """Insert one full run/task/worker/lease chain with the given statuses,
    returning the lease_id. Test-only helper — talks directly to the pool
    rather than going through the normal lifecycle methods so each field
    can be set independently."""
    run_id = uuid.uuid4()
    worker_id = uuid.uuid4()
    task_id = uuid.uuid4()
    lease_id = uuid.uuid4()
    range_id = uuid.uuid4()
    async with store._pool.connection() as conn:  # noqa: SLF001
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO scheduler_worker_runs (run_id, range_id, provider, status, created_at, metadata)
                VALUES (%(rid)s, %(range_id)s, 'mock', %(status)s, now(), '{}'::jsonb)
                """,
                {"rid": run_id, "range_id": range_id, "status": run_status},
            )
            await cur.execute(
                """
                INSERT INTO worker_instances (worker_id, run_id, range_id, provider, status, expires_at)
                VALUES (%(wid)s, %(rid)s, %(range_id)s, 'mock', %(status)s, now() + interval '1 hour')
                """,
                {"wid": worker_id, "rid": run_id, "range_id": range_id, "status": worker_status},
            )
            await cur.execute(
                """
                INSERT INTO worker_tasks (task_id, run_id, range_id, task_type, status, payload)
                VALUES (%(tid)s, %(rid)s, %(range_id)s, 'CPU_BENCHMARK', %(status)s, '{}'::jsonb)
                """,
                {"tid": task_id, "rid": run_id, "range_id": range_id, "status": task_status},
            )
            await cur.execute(
                """
                INSERT INTO worker_leases (lease_id, task_id, worker_id, status, expires_at)
                VALUES (%(lid)s, %(tid)s, %(wid)s, %(status)s, %(exp)s)
                """,
                {"lid": lease_id, "tid": task_id, "wid": worker_id, "status": lease_status, "exp": expires_at},
            )
    return lease_id


@pytest.mark.asyncio
async def test_release_stale_lease_releases_when_fully_dead(store):
    lease_id = await _seed(store, expires_at=datetime.now(timezone.utc) - timedelta(hours=2, minutes=50))
    outcome = await store.release_stale_lease(lease_id)
    assert outcome == "released"

    # idempotent: calling again is a safe no-op, not an error
    outcome2 = await store.release_stale_lease(lease_id)
    assert outcome2 == "already_released"


@pytest.mark.asyncio
async def test_release_stale_lease_refuses_when_not_expired(store):
    lease_id = await _seed(store, expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
    with pytest.raises(ValueError, match="not yet expired"):
        await store.release_stale_lease(lease_id)


@pytest.mark.asyncio
async def test_release_stale_lease_refuses_when_worker_not_terminal(store):
    lease_id = await _seed(
        store,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        worker_status="RUNNING",
    )
    with pytest.raises(ValueError, match="worker status"):
        await store.release_stale_lease(lease_id)


@pytest.mark.asyncio
async def test_release_stale_lease_refuses_when_run_not_terminal(store):
    lease_id = await _seed(
        store,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        run_status="RUNNING",
    )
    with pytest.raises(ValueError, match="run status"):
        await store.release_stale_lease(lease_id)


@pytest.mark.asyncio
async def test_release_stale_lease_unknown_id_raises(store):
    with pytest.raises(ValueError, match="does not exist"):
        await store.release_stale_lease(uuid.uuid4())
