"""``EventGateway``: the one object that implements ADR-011 end to end —
append-then-publish on the write side, replay-then-live-tail-with-no-gap on
the read side. ``apps/api``'s WS/SSE route (whoever wires it — see
``packages/events/README.md`` "Wire contract") should be a thin transport
adapter around this class, not reimplement any of this logic itself.

Correction versus ADR-011 §2's literal step ordering
------------------------------------------------------
ADR-011 §2 describes: (1) query replay batch, (2) stream it, (3) *then*
subscribe to the live channel, (4) drop a live message whose seq is
`<=` the last replayed seq (dedup for the race where step 1's snapshot and
step 3's subscribe overlap).

That literal ordering has a real gap, not just a dup risk: Redis pub-sub
delivers only to subscribers that are *already* subscribed at publish
time. Any event appended+published between step 1's query and step 3's
subscribe taking effect is never delivered to this connection at all —
dedup logic can't recover data that was never received.

This implementation subscribes to the live channel *first*, then runs the
replay query, then drains/dedupes. Once subscribed, the Redis client has
already queued (server- and socket-buffer-side) anything published from
that instant on, even before this code calls the equivalent of "read the
next message" — so nothing published during the replay query can be
missed. The dedup-by-seq check ADR-011 specifies still runs (now against
the *other* overlap direction: a live message for something the replay
query already covered), and an explicit gap-heal path re-queries Postgres
if the live tail ever skips a seq (e.g. a dropped connection to Redis),
giving true "no gap, no duplicate" rather than "no duplicate, small gap
window accepted."
"""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Optional

from .._base import GhostRangeEvent
from .models import StoredEvent
from .postgres import PostgresEventStore
from .pubsub import RedisBus


class EventGateway:
    def __init__(self, store: PostgresEventStore, bus: RedisBus) -> None:
        self._store = store
        self._bus = bus

    @property
    def store(self) -> PostgresEventStore:
        return self._store

    @property
    def bus(self) -> RedisBus:
        return self._bus

    async def append_and_publish(
        self,
        range_id: uuid.UUID,
        event: GhostRangeEvent,
        *,
        source: str,
        world_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[uuid.UUID] = None,
    ) -> StoredEvent:
        """The only method producers should call to emit an event. Appends
        durably (assigning ``seq``) first, then publishes live — per
        ADR-011 §1, in that order, non-negotiably.

        A publish failure (e.g. Redis briefly unreachable) is swallowed,
        not raised: the durable append already succeeded, which is the
        operation that matters for correctness. A live subscriber that
        missed the publish will pick the event up on its next reconnect
        (full replay) or the next gap-heal cycle in ``stream()`` below.
        Producers therefore never need Redis to be up to make progress.
        """
        stored = await self._store.append(
            range_id, event, source=source, world_id=world_id, correlation_id=correlation_id
        )
        try:
            await self._bus.publish(stored)
        except Exception:
            pass
        return stored

    async def append_payload_and_publish(
        self,
        range_id: uuid.UUID,
        payload: dict[str, Any],
        *,
        source: str,
        world_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[uuid.UUID] = None,
    ) -> StoredEvent:
        stored = await self._store.append_payload(
            range_id, payload, source=source, world_id=world_id, correlation_id=correlation_id
        )
        try:
            await self._bus.publish(stored)
        except Exception:
            pass
        return stored

    async def stream(
        self, range_id: uuid.UUID, since_seq: int = 0
    ) -> AsyncIterator[StoredEvent]:
        """Yield every event for ``range_id`` with ``seq > since_seq``, in
        strict ascending ``seq`` order, exactly once each: first the
        durably-replayed catch-up batch, then a live, gap-healing tail that
        runs until the caller stops iterating (e.g. the WS connection
        closes).

        This is the one function the "replay + live handoff, no gap, no
        duplicate" test exercises directly.
        """
        async with self._bus.subscribe(range_id) as live:
            # Subscribed now — nothing published from this instant on can
            # be missed (see module docstring). Only after this does the
            # replay query run.
            replayed = await self._store.replay(range_id, since_seq)
            last_seq = since_seq
            for stored in replayed:
                last_seq = stored.seq
                yield stored

            async for live_event in live:
                if live_event.range_id != range_id:
                    continue  # defensive; channel is already range-scoped

                if live_event.seq <= last_seq:
                    # Duplicate: either the replay batch above already
                    # covered it, or an earlier gap-heal already did.
                    continue

                if live_event.seq == last_seq + 1:
                    last_seq = live_event.seq
                    yield live_event
                    continue

                # Gap: the live tail skipped ahead of last_seq+1 (e.g. a
                # transient Redis hiccup dropped an intervening message).
                # Postgres is the source of truth — re-replay from
                # last_seq to fetch exactly what's missing, in order.
                catchup = await self._store.replay(range_id, last_seq)
                for stored in catchup:
                    if stored.seq > last_seq:
                        last_seq = stored.seq
                        yield stored

                if live_event.seq > last_seq:
                    # Still ahead after healing (shouldn't happen given
                    # append always precedes publish, but never silently
                    # drop real data if it does).
                    last_seq = live_event.seq
                    yield live_event

    async def stream_client_events(
        self, range_id: uuid.UUID, since_seq: int = 0
    ) -> AsyncIterator[dict]:
        """Convenience wrapper around ``stream()`` for the actual WS/SSE
        route: yields the flat, apps/web-compatible client dict
        (``StoredEvent.to_client_event()``) directly, so ``apps/api`` never
        needs to import ``StoredEvent`` itself — it can just
        ``json.dumps(event)`` (WS) or format it as an SSE ``data:`` line.
        """
        async for stored in self.stream(range_id, since_seq):
            yield stored.to_client_event()


__all__ = ["EventGateway"]
