"""In-process event log + SSE stream for mock E2E and local dev without Postgres."""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional

from ghostrange_events._base import GhostRangeEvent
from ghostrange_events.store.models import StoredEvent


class MemoryEventGateway:
    def __init__(self) -> None:
        self._rows: dict[uuid.UUID, list[StoredEvent]] = defaultdict(list)
        self._queues: dict[uuid.UUID, list[asyncio.Queue[StoredEvent]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def append(
        self,
        range_id: uuid.UUID,
        event: GhostRangeEvent,
        *,
        source: str,
        world_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[uuid.UUID] = None,
    ) -> StoredEvent:
        payload = event.model_dump(mode="json")
        return await self._append_payload(
            range_id, payload, source=source, world_id=world_id, correlation_id=correlation_id
        )

    async def append_legacy(
        self,
        range_id: uuid.UUID,
        payload: dict[str, Any],
        *,
        source: str,
        world_id: Optional[uuid.UUID] = None,
    ) -> StoredEvent:
        return await self._append_payload(
            range_id, payload, source=source, world_id=world_id, correlation_id=None
        )

    async def _append_payload(
        self,
        range_id: uuid.UUID,
        payload: dict[str, Any],
        *,
        source: str,
        world_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[uuid.UUID] = None,
    ) -> StoredEvent:
        async with self._lock:
            seq = len(self._rows[range_id]) + 1
            event_name = str(payload.get("event_name") or payload.get("type") or "unknown")
            event_id = uuid.UUID(str(payload.get("event_id"))) if payload.get("event_id") else uuid.uuid4()
            occurred_raw = payload.get("occurred_at")
            if isinstance(occurred_raw, str):
                occurred_at = datetime.fromisoformat(occurred_raw.replace("Z", "+00:00"))
            else:
                occurred_at = datetime.now(timezone.utc)
            stored = StoredEvent(
                event_id=event_id,
                range_id=range_id,
                world_id=world_id,
                seq=seq,
                event_type=event_name,
                event_version=str(payload.get("schema_version", "1")),
                occurred_at=occurred_at,
                source=source,
                correlation_id=correlation_id,
                payload=payload,
            )
            self._rows[range_id].append(stored)
            for q in self._queues[range_id]:
                q.put_nowait(stored)
            return stored

    async def replay(self, range_id: uuid.UUID, since_seq: int = 0) -> list[StoredEvent]:
        return [r for r in self._rows.get(range_id, []) if r.seq > since_seq]

    def max_seq(self, range_id: uuid.UUID) -> int:
        rows = self._rows.get(range_id, [])
        return rows[-1].seq if rows else 0

    async def stream(self, range_id: uuid.UUID, since_seq: int = 0) -> AsyncIterator[StoredEvent]:
        q: asyncio.Queue[StoredEvent] = asyncio.Queue()
        self._queues[range_id].append(q)
        try:
            for row in await self.replay(range_id, since_seq):
                yield row
            last = self.max_seq(range_id)
            while True:
                row = await q.get()
                if row.seq > last:
                    last = row.seq
                    yield row
        finally:
            self._queues[range_id].remove(q)
