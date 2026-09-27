"""Lease reconciliation: safely close out stale ``worker_leases`` rows.

This is a real, reusable operational tool — not a one-off script — for the
recurring case where a worker lease's task/worker/run all reached a
terminal state (completed or failed) but the lease row itself never got
its terminal ``UPDATE`` (e.g. a crash between ``complete_task``'s task
update and its lease update, or a run that failed/was torn down out of
band). ``WorkerStore.release_stale_lease`` (see ``worker_store.py``) does
the actual, guarded work: it re-verifies inside the same transaction that
a lease is truly expired *and* that its task/worker/run are all terminal
before touching anything, and raises rather than silently skipping a lease
that turns out not to be dead. This module is just the CLI wrapper around
that primitive, so an operator (or this script) never has to hand-write
ad-hoc SQL against production to do it.

Usage:
    python -m ghostrange_api.reconcile_leases <lease_id> [<lease_id> ...]
    python -m ghostrange_api.reconcile_leases --apply <lease_id> ...

Defaults to ``--dry-run`` (report what *would* happen, touch nothing).
Requires ``POSTGRES_DSN`` (or ``DATABASE_URL``) in the environment, same
as the API server itself.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .config import Settings
from .worker_store import WorkerStore


async def _dry_run_check(store: WorkerStore, lease_id: uuid.UUID) -> dict[str, Any]:
    """Read-only preview: reuses the exact same eligibility query
    ``release_stale_lease`` runs, but never issues the UPDATE."""
    async with store._pool.connection() as conn:  # noqa: SLF001 - CLI is an authorized collaborator
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
                """,
                {"lid": lease_id},
            )
            row = await cur.fetchone()
    if row is None:
        return {"lease_id": str(lease_id), "eligible": False, "reason": "lease does not exist"}
    if row["lease_status"] != "ACTIVE":
        return {"lease_id": str(lease_id), "eligible": False, "reason": f"lease status is {row['lease_status']!r}, not ACTIVE"}
    now = datetime.now(timezone.utc)
    if row["expires_at"] >= now:
        return {"lease_id": str(lease_id), "eligible": False, "reason": f"not yet expired ({row['expires_at']})"}
    if row["task_status"] not in WorkerStore._TERMINAL_TASK_STATUSES:
        return {"lease_id": str(lease_id), "eligible": False, "reason": f"task status {row['task_status']!r} not terminal"}
    if row["worker_status"] not in WorkerStore._TERMINAL_WORKER_STATUSES:
        return {"lease_id": str(lease_id), "eligible": False, "reason": f"worker status {row['worker_status']!r} not terminal"}
    if row["run_status"] not in WorkerStore._TERMINAL_RUN_STATUSES:
        return {"lease_id": str(lease_id), "eligible": False, "reason": f"run status {row['run_status']!r} not terminal"}
    return {"lease_id": str(lease_id), "eligible": True, "reason": "expired and all associated records terminal"}


async def _run(lease_ids: list[str], *, apply: bool) -> list[dict[str, Any]]:
    settings = Settings.from_env()
    if not settings.postgres_dsn:
        raise RuntimeError("POSTGRES_DSN (or DATABASE_URL) is required to reconcile leases")
    pool = AsyncConnectionPool(settings.postgres_dsn, min_size=1, max_size=2, open=False)
    await pool.open(wait=True, timeout=30)
    store = WorkerStore(pool)
    results: list[dict[str, Any]] = []
    try:
        for raw_id in lease_ids:
            lease_id = uuid.UUID(raw_id)
            if not apply:
                results.append(await _dry_run_check(store, lease_id))
                continue
            try:
                outcome = await store.release_stale_lease(lease_id)
                results.append({"lease_id": raw_id, "outcome": outcome})
            except ValueError as exc:
                results.append({"lease_id": raw_id, "outcome": "refused", "reason": str(exc)})
    finally:
        await pool.close()
    return results


def cli() -> None:
    parser = argparse.ArgumentParser(description="Reconcile stale worker_leases rows")
    parser.add_argument("lease_ids", nargs="+", help="lease_id(s) to reconcile")
    parser.add_argument("--apply", action="store_true", help="Actually release eligible leases (default: dry-run report only)")
    args = parser.parse_args()

    results = asyncio.run(_run(args.lease_ids, apply=args.apply))
    print(json.dumps({"dry_run": not args.apply, "results": results}, indent=2))
    if not args.apply:
        sys.exit(0)
    if any(r.get("outcome") == "refused" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    cli()
