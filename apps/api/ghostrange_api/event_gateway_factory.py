"""Production EventGateway (Postgres + Redis) or in-memory fallback."""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Optional

from ghostrange_events._base import GhostRangeEvent
from ghostrange_events.registry import parse_event
from ghostrange_events.store.gateway import EventGateway
from ghostrange_events.store.models import StoredEvent
from ghostrange_events.store.postgres import PostgresEventStore
from ghostrange_events.store.pubsub import RedisBus

from .memory_events import MemoryEventGateway


class DurableEventGateway:
    """Same surface as MemoryEventGateway for apps/api orchestration."""

    def __init__(self, inner: EventGateway) -> None:
        self._inner = inner

    async def append(
        self,
        range_id: uuid.UUID,
        event: GhostRangeEvent,
        *,
        source: str,
        world_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[uuid.UUID] = None,
    ) -> StoredEvent:
        return await self._inner.append_and_publish(
            range_id, event, source=source, world_id=world_id, correlation_id=correlation_id
        )

    async def append_legacy(
        self,
        range_id: uuid.UUID,
        payload: dict[str, Any],
        *,
        source: str,
        world_id: Optional[uuid.UUID] = None,
    ) -> StoredEvent:
        try:
            event = parse_event(payload)
            return await self.append(range_id, event, source=source, world_id=world_id)
        except Exception:
            return await self._inner.append_payload_and_publish(
                range_id, payload, source=source, world_id=world_id
            )

    async def replay(self, range_id: uuid.UUID, since_seq: int = 0) -> list[StoredEvent]:
        return await self._inner.store.replay(range_id, since_seq)

    def max_seq(self, range_id: uuid.UUID) -> int:
        # Snapshot handler computes seq from replay; sync callers should too.
        return 0

    async def stream(self, range_id: uuid.UUID, since_seq: int = 0) -> AsyncIterator[StoredEvent]:
        async for row in self._inner.stream(range_id, since_seq):
            yield row


async def build_event_gateway(
    postgres_dsn: str | None,
    redis_url: str | None,
    *,
    require_durable: bool = False,
) -> tuple[MemoryEventGateway | DurableEventGateway, EventGateway | None, PostgresEventStore | None]:
    if require_durable and not (postgres_dsn and redis_url):
        raise RuntimeError("Durable event store required but POSTGRES_DSN/REDIS_URL missing")
    if postgres_dsn and redis_url:
        store = await PostgresEventStore.connect(postgres_dsn, min_size=1, max_size=8)
        bus = RedisBus(redis_url)
        inner = EventGateway(store, bus)
        return DurableEventGateway(inner), inner, store
    return MemoryEventGateway(), None, None
