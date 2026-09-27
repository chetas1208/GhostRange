"""Persist GhostCostLedger to PostgreSQL (same cluster as events)."""

from __future__ import annotations

import json
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from ghostrange_cost.ledger import GhostCostLedger

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cost_ledger_campaigns (
  campaign_id TEXT PRIMARY KEY,
  state JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS operation_timing_samples (
  id BIGSERIAL PRIMARY KEY,
  range_id TEXT NOT NULL,
  operation_type TEXT NOT NULL,
  provider TEXT,
  region TEXT,
  resource_class TEXT,
  task_class TEXT,
  queued_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  elapsed_ms INT NOT NULL,
  success BOOLEAN NOT NULL DEFAULT TRUE,
  failure_type TEXT,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_operation_timing_type ON operation_timing_samples (operation_type, provider, region);
"""


class CostLedgerPersistence:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def ensure_schema(self) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(_SCHEMA)

    async def load_into(self, ledger: GhostCostLedger) -> None:
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("SELECT campaign_id, state FROM cost_ledger_campaigns ORDER BY updated_at DESC LIMIT 1")
                row = await cur.fetchone()
                if row and row["state"]:
                    ledger.import_state(row["state"])

    async def save_campaign(self, campaign_id: str, ledger: GhostCostLedger) -> None:
        state = ledger.export_state()
        state["campaign_id"] = campaign_id
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO cost_ledger_campaigns (campaign_id, state, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (campaign_id) DO UPDATE SET state = EXCLUDED.state, updated_at = NOW()
                """,
                (campaign_id, Jsonb(state)),
            )

    async def load_campaign(self, campaign_id: str) -> dict[str, Any] | None:
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT state FROM cost_ledger_campaigns WHERE campaign_id = %s",
                    (campaign_id,),
                )
                row = await cur.fetchone()
                return row["state"] if row else None
