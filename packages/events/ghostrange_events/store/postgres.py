"""The durable half of ADR-011's design: append-then-publish's "append",
and the replay query a fresh/reconnecting WS client's catch-up batch comes
from.

Requires the ``store`` extra (``pip install -e "packages/events[store]"``):
``psycopg[binary]`` + ``psycopg-pool``. Kept out of this package's core
dependencies so anything that only needs the event *schemas* (e.g.
``apps/web``'s Python tooling, if any, or a unit test that just builds
payload objects) doesn't have to pull in a Postgres driver.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from .._base import GhostRangeEvent
from .models import StoredEvent

_SCHEMA_SQL = (Path(__file__).parent / "schema.sql").read_text()


class SeqAssignmentError(RuntimeError):
    """Raised if the per-range seq counter upsert somehow returns nothing —
    should be unreachable given the UPSERT always affects exactly one row,
    but the failure mode is loud rather than silently appending with a
    wrong/duplicate seq.
    """


class PostgresEventStore:
    """Durable, per-range-ordered event log backed by Postgres.

    Every write path in GhostRange that needs to be observable (see
    ``ghostrange_events`` README's producer list) calls ``append()`` here
    *before* publishing live — this class only does the durable half; the
    live publish is ``store.pubsub.RedisBus.publish()``, composed together
    in ``store.gateway.EventGateway`` so producers get one call that does
    both, in the correct order, per ADR-011 §1.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, dsn: str, *, min_size: int = 1, max_size: int = 10) -> "PostgresEventStore":
        pool = AsyncConnectionPool(dsn, min_size=min_size, max_size=max_size, open=False)
        await pool.open(wait=True, timeout=30)
        store = cls(pool)
        await store.ensure_schema()
        return store

    async def ensure_schema(self) -> None:
        """Idempotent: creates ``event_log``/``range_seq_counters`` if they
        don't exist yet. Safe to call on every process startup.
        """
        async with self._pool.connection() as conn:
            await conn.execute(_SCHEMA_SQL)

    async def close(self) -> None:
        await self._pool.close()

    async def append(
        self,
        range_id: uuid.UUID,
        event: GhostRangeEvent,
        *,
        source: str,
        world_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[uuid.UUID] = None,
    ) -> StoredEvent:
        """Durably append ``event`` under ``range_id``, assigning the next
        per-range ``seq`` atomically, and return the stored row.

        Concurrency safety (ADR-011's flagged concern): seq assignment is a
        single ``INSERT ... ON CONFLICT DO UPDATE ... RETURNING`` against
        ``range_seq_counters`` inside the same transaction as the
        ``event_log`` insert. This is one round-trip, race-free under
        concurrent appends to the *same* range_id (Postgres serializes
        concurrent UPDATEs to the same row), and never blocks appends to
        *different* ranges against each other (different rows, no shared
        lock) — deliberately not a naive ``SELECT MAX(seq)+1`` read-then-
        write, which would race.
        """
        payload = event.model_dump(mode="json")
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        INSERT INTO range_seq_counters (range_id, next_seq)
                        VALUES (%(range_id)s, 2)
                        ON CONFLICT (range_id)
                        DO UPDATE SET next_seq = range_seq_counters.next_seq + 1
                        RETURNING next_seq - 1 AS assigned_seq
                        """,
                        {"range_id": range_id},
                    )
                    row = await cur.fetchone()
                    if row is None:
                        raise SeqAssignmentError(
                            f"seq upsert returned no row for range_id={range_id}"
                        )
                    seq = row["assigned_seq"]

                    await cur.execute(
                        """
                        INSERT INTO event_log (
                            event_id, range_id, world_id, seq, event_type,
                            event_version, occurred_at, source, correlation_id, payload
                        ) VALUES (
                            %(event_id)s, %(range_id)s, %(world_id)s, %(seq)s, %(event_type)s,
                            %(event_version)s, %(occurred_at)s, %(source)s, %(correlation_id)s,
                            %(payload)s
                        )
                        """,
                        {
                            "event_id": event.event_id,
                            "range_id": range_id,
                            "world_id": world_id,
                            "seq": seq,
                            "event_type": event.event_name.value,
                            "event_version": event.schema_version,
                            "occurred_at": event.occurred_at,
                            "source": source,
                            "correlation_id": correlation_id,
                            "payload": Jsonb(payload),
                        },
                    )

        return StoredEvent(
            event_id=event.event_id,
            range_id=range_id,
            world_id=world_id,
            seq=seq,
            event_type=event.event_name.value,
            event_version=event.schema_version,
            occurred_at=event.occurred_at,
            source=source,
            correlation_id=correlation_id,
            payload=payload,
        )

    async def append_payload(
        self,
        range_id: uuid.UUID,
        payload: dict[str, Any],
        *,
        source: str,
        world_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[uuid.UUID] = None,
    ) -> StoredEvent:
        """Durably store a legacy/client dict (e.g. golden_path.*) without registry typing."""
        event_name = str(payload.get("event_name") or payload.get("type") or "unknown")
        event_id = uuid.UUID(str(payload["event_id"])) if payload.get("event_id") else uuid.uuid4()
        occurred_raw = payload.get("occurred_at")
        if isinstance(occurred_raw, str):
            occurred_at = datetime.fromisoformat(occurred_raw.replace("Z", "+00:00"))
        else:
            occurred_at = datetime.now(timezone.utc)
        event_version = str(payload.get("schema_version", "1"))

        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        INSERT INTO range_seq_counters (range_id, next_seq)
                        VALUES (%(range_id)s, 2)
                        ON CONFLICT (range_id)
                        DO UPDATE SET next_seq = range_seq_counters.next_seq + 1
                        RETURNING next_seq - 1 AS assigned_seq
                        """,
                        {"range_id": range_id},
                    )
                    row = await cur.fetchone()
                    if row is None:
                        raise SeqAssignmentError(
                            f"seq upsert returned no row for range_id={range_id}"
                        )
                    seq = row["assigned_seq"]

                    await cur.execute(
                        """
                        INSERT INTO event_log (
                            event_id, range_id, world_id, seq, event_type,
                            event_version, occurred_at, source, correlation_id, payload
                        ) VALUES (
                            %(event_id)s, %(range_id)s, %(world_id)s, %(seq)s, %(event_type)s,
                            %(event_version)s, %(occurred_at)s, %(source)s, %(correlation_id)s,
                            %(payload)s
                        )
                        """,
                        {
                            "event_id": event_id,
                            "range_id": range_id,
                            "world_id": world_id,
                            "seq": seq,
                            "event_type": event_name,
                            "event_version": event_version,
                            "occurred_at": occurred_at,
                            "source": source,
                            "correlation_id": correlation_id,
                            "payload": Jsonb(payload),
                        },
                    )

        return StoredEvent(
            event_id=event_id,
            range_id=range_id,
            world_id=world_id,
            seq=seq,
            event_type=event_name,
            event_version=event_version,
            occurred_at=occurred_at,
            source=source,
            correlation_id=correlation_id,
            payload=payload,
        )

    async def replay(self, range_id: uuid.UUID, since_seq: int = 0) -> list[StoredEvent]:
        """Every durably-appended event for ``range_id`` with
        ``seq > since_seq``, in ascending ``seq`` order. ``since_seq=0``
        (the default) returns the full history — a fresh client's initial
        load is exactly this call.
        """
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT event_id, range_id, world_id, seq, event_type,
                           event_version, occurred_at, source, correlation_id, payload
                    FROM event_log
                    WHERE range_id = %(range_id)s AND seq > %(since_seq)s
                    ORDER BY seq ASC
                    """,
                    {"range_id": range_id, "since_seq": since_seq},
                )
                rows = await cur.fetchall()
        return [
            StoredEvent(
                event_id=row["event_id"],
                range_id=row["range_id"],
                world_id=row["world_id"],
                seq=row["seq"],
                event_type=row["event_type"],
                event_version=row["event_version"],
                occurred_at=row["occurred_at"],
                source=row["source"],
                correlation_id=row["correlation_id"],
                payload=row["payload"],
            )
            for row in rows
        ]

    async def latest_seq(self, range_id: uuid.UUID) -> int:
        """Highest durably-appended seq for ``range_id``, or 0 if none."""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COALESCE(MAX(seq), 0) FROM event_log WHERE range_id = %(range_id)s",
                    {"range_id": range_id},
                )
                row = await cur.fetchone()
        return int(row[0]) if row else 0


__all__ = ["PostgresEventStore", "SeqAssignmentError"]
