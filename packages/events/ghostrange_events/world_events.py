"""Payloads for the world.* events (World lifecycle + forking).

The frontend's multiverse view materializes a World node only after
``world.ready`` (never before, mirroring the ComputeNode rule for compute),
and draws a fork edge from ``world.forked`` alone — that payload therefore
must carry both endpoints and the reason, not just the child.
"""

from __future__ import annotations

import uuid
from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import GhostRangeEvent
from .names import EventName


class WorldRequestedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.WORLD_REQUESTED
    event_name: Literal[EventName.WORLD_REQUESTED] = EventName.WORLD_REQUESTED

    world_id: uuid.UUID
    range_id: uuid.UUID
    parent_world_id: Optional[uuid.UUID] = Field(
        default=None, description="None iff this is the Range's root World"
    )
    requested_by: str


class WorldProvisioningV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.WORLD_PROVISIONING
    event_name: Literal[EventName.WORLD_PROVISIONING] = EventName.WORLD_PROVISIONING

    world_id: uuid.UUID
    range_id: uuid.UUID


class WorldReadyV1(GhostRangeEvent):
    """Frontend rule: a World node is materialized in the 3D view only
    after this event arrives, never speculatively on world.requested.
    """

    EVENT_NAME: ClassVar[EventName] = EventName.WORLD_READY
    event_name: Literal[EventName.WORLD_READY] = EventName.WORLD_READY

    world_id: uuid.UUID
    range_id: uuid.UUID
    asset_count: int = Field(..., ge=0)
    network_count: int = Field(..., ge=0)


class WorldForkedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.WORLD_FORKED
    event_name: Literal[EventName.WORLD_FORKED] = EventName.WORLD_FORKED

    range_id: uuid.UUID
    parent_world_id: uuid.UUID
    child_world_id: uuid.UUID
    fork_reason: str
    created_by: str = Field(..., description="Agent id, 'scheduler', or a human identifier")


class WorldDestroyingV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.WORLD_DESTROYING
    event_name: Literal[EventName.WORLD_DESTROYING] = EventName.WORLD_DESTROYING

    world_id: uuid.UUID
    range_id: uuid.UUID
    reason: Optional[str] = None


class WorldDestroyedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.WORLD_DESTROYED
    event_name: Literal[EventName.WORLD_DESTROYED] = EventName.WORLD_DESTROYED

    world_id: uuid.UUID
    range_id: uuid.UUID
    reason: Optional[str] = None


__all__ = [
    "WorldRequestedV1",
    "WorldProvisioningV1",
    "WorldReadyV1",
    "WorldForkedV1",
    "WorldDestroyingV1",
    "WorldDestroyedV1",
]
