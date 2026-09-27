"""The live half of ADR-011's design: best-effort Redis/Valkey pub-sub
delivery, published *after* the durable append (ADR-011 §1: "The append
happens first ... the publish is best-effort live delivery").

Requires the ``store`` extra (``redis>=5``, async client via
``redis.asyncio``).
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from redis.asyncio import Redis

from .models import StoredEvent


def channel_name(range_id: uuid.UUID) -> str:
    """The Redis channel one Range's events are published to, per
    ADR-011 §1 ("the Redis/Valkey channel for that range_id ... channel
    `range.{range_id}.events`").
    """
    return f"range.{range_id}.events"


class RedisBus:
    """Thin wrapper: publish a ``StoredEvent`` to its Range's channel,
    subscribe to a Range's channel and get an async iterator of
    ``StoredEvent`` back. No buffering/backlog logic lives here — that's
    the whole reason ``event_log`` (``postgres.py``) exists; this class is
    deliberately dumb, matching Redis pub-sub's own "no durability, best
    effort, fire-and-forget" semantics (Decisions.md #4 / ADR-011 Context).
    """

    def __init__(self, client: Redis) -> None:
        self._client = client

    @classmethod
    async def connect(cls, url: str) -> "RedisBus":
        client = Redis.from_url(url, decode_responses=True)
        await client.ping()
        return cls(client)

    async def close(self) -> None:
        await self._client.aclose()

    async def publish(self, stored_event: StoredEvent) -> None:
        await self._client.publish(
            channel_name(stored_event.range_id), json.dumps(stored_event.to_redis_message())
        )

    @asynccontextmanager
    async def subscribe(self, range_id: uuid.UUID) -> AsyncIterator["LiveSubscription"]:
        """Async context manager yielding a ``LiveSubscription``.

        Callers MUST enter this context (i.e. be subscribed) *before* doing
        anything that depends on "nothing published after this point will
        be missed" — see ``store/gateway.py``'s ``EventGateway.stream()``
        docstring for exactly why the subscribe-then-replay ordering (not
        replay-then-subscribe) is what actually closes the gap.
        """
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel_name(range_id))
        try:
            yield LiveSubscription(pubsub)
        finally:
            await pubsub.unsubscribe(channel_name(range_id))
            await pubsub.aclose()


class LiveSubscription:
    """An active subscription to one Range's live channel. Once entered
    (``RedisBus.subscribe`` has returned), any message the server sends is
    queued by the underlying client even before this object's consumer
    starts iterating — that queuing (not any buffering logic of ours) is
    what makes "subscribe first, query Postgres second" safe.
    """

    def __init__(self, pubsub) -> None:
        self._pubsub = pubsub

    async def __aiter__(self) -> AsyncIterator[StoredEvent]:
        async for message in self._pubsub.listen():
            if message.get("type") != "message":
                continue  # subscribe/unsubscribe/psubscribe control messages
            data = json.loads(message["data"])
            yield StoredEvent.from_redis_message(data)

    async def get(self, *, timeout: float | None = None) -> StoredEvent | None:
        """Poll for a single message without blocking forever; returns
        ``None`` on timeout. Used by tests / any caller that wants a
        non-generator drain-loop instead of ``async for``.
        """
        message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
        if message is None:
            return None
        data = json.loads(message["data"])
        return StoredEvent.from_redis_message(data)


__all__ = ["RedisBus", "LiveSubscription", "channel_name"]
