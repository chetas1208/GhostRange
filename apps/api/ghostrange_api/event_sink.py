from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from ghostrange_events._base import GhostRangeEvent

from .memory_events import MemoryEventGateway


class AsyncGatewaySink:
    """Bridges sync ``RangeRuntimeEngine`` publishes to async ``MemoryEventGateway``."""

    def __init__(
        self,
        gateway: MemoryEventGateway,
        range_id: uuid.UUID,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self._gateway = gateway
        self._range_id = range_id
        self._loop = loop

    def publish(self, event: object) -> None:
        if not isinstance(event, GhostRangeEvent):
            return
        world_id = getattr(event, "world_id", None)
        coro = self._gateway.append(
            self._range_id,
            event,
            source="range-runtime",
            world_id=world_id,
        )
        loop = self._loop
        if loop is None:
            return
        loop.call_soon_threadsafe(lambda: asyncio.ensure_future(coro))
