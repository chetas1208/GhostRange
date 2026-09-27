"""Durable persistence for Range lifecycle transitions.

See README.md "Persistence choice" for why this is SQLite (stdlib
``sqlite3``, no new dependency) rather than Postgres for this pass: no
Postgres wiring existed anywhere in the repo yet, and standing up a
second, uncoordinated schema risks diverging from Agent 08's `event_log`
work. This module's public interface (``append``, ``history``,
``latest_state``, ``save_snapshot``, ``load_snapshot``,
``all_range_ids``) is deliberately small so a future Postgres-backed
implementation can satisfy the same shape.

Two tables:

- ``range_transitions``: append-only audit log, exactly the tuple the
  brief specifies (range_id, world_id, previous_state, new_state,
  reason, correlation_id, timestamp). Never updated or deleted.
- ``range_snapshots``: one row per range_id, upserted on every
  transition, holding the full serialized ``RangeV1`` — a cache derived
  from the log (see ``rebuild_range_state``), not a second source of
  truth. Restarting a process reads this for O(1) resume instead of
  replaying the whole log, but the log is what tests check for
  durability/round-trip correctness.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from ghostrange_contracts._base import Id
from ghostrange_contracts.enums import RangeLifecycleState
from ghostrange_contracts.range import RangeV1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS range_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    range_id TEXT NOT NULL,
    world_id TEXT,
    previous_state TEXT,
    new_state TEXT NOT NULL,
    reason TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_range_transitions_range_id
    ON range_transitions (range_id, id);

CREATE TABLE IF NOT EXISTS range_snapshots (
    range_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class TransitionRecord:
    """One durable row of ``range_transitions``."""

    id: int
    range_id: Id
    world_id: Optional[Id]
    previous_state: Optional[RangeLifecycleState]
    new_state: RangeLifecycleState
    reason: str
    correlation_id: str
    timestamp: datetime


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_record(row: sqlite3.Row) -> TransitionRecord:
    return TransitionRecord(
        id=row["id"],
        range_id=uuid.UUID(row["range_id"]),
        world_id=uuid.UUID(row["world_id"]) if row["world_id"] else None,
        previous_state=(
            RangeLifecycleState(row["previous_state"]) if row["previous_state"] else None
        ),
        new_state=RangeLifecycleState(row["new_state"]),
        reason=row["reason"],
        correlation_id=row["correlation_id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
    )


class SqliteTransitionStore:
    """Append-only, file-backed transition log + snapshot cache.

    Every write is committed immediately (no batching) so a crash right
    after ``append``/``save_snapshot`` returns never loses the write —
    "durable" is not aspirational here, it is checked directly by
    ``tests/test_persistence.py``'s round-trip tests (write, reopen a
    *new* store instance against the same file, confirm identical data).
    """

    def __init__(self, db_path: Union[str, Path]) -> None:
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SqliteTransitionStore":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- append-only transition log -----------------------------------

    def append(
        self,
        *,
        range_id: Id,
        world_id: Optional[Id],
        previous_state: Optional[RangeLifecycleState],
        new_state: RangeLifecycleState,
        reason: str,
        correlation_id: str,
        timestamp: Optional[datetime] = None,
    ) -> TransitionRecord:
        ts = timestamp or _utc_now()
        cur = self._conn.execute(
            """
            INSERT INTO range_transitions
                (range_id, world_id, previous_state, new_state, reason, correlation_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(range_id),
                str(world_id) if world_id else None,
                previous_state.value if previous_state else None,
                new_state.value,
                reason,
                correlation_id,
                ts.isoformat(),
            ),
        )
        row_id = cur.lastrowid
        return TransitionRecord(
            id=row_id,
            range_id=range_id,
            world_id=world_id,
            previous_state=previous_state,
            new_state=new_state,
            reason=reason,
            correlation_id=correlation_id,
            timestamp=ts,
        )

    def history(self, range_id: Id) -> list[TransitionRecord]:
        rows = self._conn.execute(
            "SELECT * FROM range_transitions WHERE range_id = ? ORDER BY id ASC",
            (str(range_id),),
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def latest_state(self, range_id: Id) -> Optional[RangeLifecycleState]:
        row = self._conn.execute(
            "SELECT new_state FROM range_transitions WHERE range_id = ? ORDER BY id DESC LIMIT 1",
            (str(range_id),),
        ).fetchone()
        return RangeLifecycleState(row["new_state"]) if row else None

    def all_range_ids(self) -> list[Id]:
        rows = self._conn.execute("SELECT DISTINCT range_id FROM range_transitions").fetchall()
        return [uuid.UUID(r["range_id"]) for r in rows]

    def rebuild_range_state(self, range_id: Id) -> Optional[RangeLifecycleState]:
        """Fold the durable log for ``range_id`` to reconstruct its
        current state from scratch (ignoring the snapshot cache
        entirely). Used to prove the snapshot cache and the log agree —
        see ``tests/test_persistence.py::test_rebuild_matches_snapshot``.
        """
        history = self.history(range_id)
        if not history:
            return None
        return history[-1].new_state

    # -- snapshot cache --------------------------------------------------

    def save_snapshot(self, range_record: RangeV1) -> None:
        payload = range_record.model_dump_json()
        now = _utc_now().isoformat()
        self._conn.execute(
            """
            INSERT INTO range_snapshots (range_id, payload_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(range_id) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (str(range_record.id), payload, now),
        )

    def load_snapshot(self, range_id: Id) -> Optional[RangeV1]:
        row = self._conn.execute(
            "SELECT payload_json FROM range_snapshots WHERE range_id = ?",
            (str(range_id),),
        ).fetchone()
        if row is None:
            return None
        return RangeV1.model_validate(json.loads(row["payload_json"]))


__all__ = ["SqliteTransitionStore", "TransitionRecord"]
