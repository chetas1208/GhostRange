"""Payloads for compute.* events.

``compute.ready`` in particular is the hard rule referenced in the task
brief: the frontend materializes a ComputeNode only after this event
arrives, never before — so its payload carries every field the UI needs to
render the node (resource class, region, provider, instance id, cost) with
no follow-up query required.
"""

from __future__ import annotations

import uuid
from typing import ClassVar, Literal, Optional

from ghostrange_contracts.enums import ComputeProvider, ResourceClass
from pydantic import Field

from ._base import GhostRangeEvent
from .names import EventName


class ComputeRequestedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.COMPUTE_REQUESTED
    event_name: Literal[EventName.COMPUTE_REQUESTED] = EventName.COMPUTE_REQUESTED

    compute_worker_id: uuid.UUID
    world_id: Optional[uuid.UUID] = None
    resource_class: ResourceClass
    region: str
    requested_by: str = Field(..., description="task id, or 'scheduler'")


class ComputeProvisioningV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.COMPUTE_PROVISIONING
    event_name: Literal[EventName.COMPUTE_PROVISIONING] = EventName.COMPUTE_PROVISIONING

    compute_worker_id: uuid.UUID
    provider: ComputeProvider
    region: str


class ComputeReadyV1(GhostRangeEvent):
    """Frontend rule: materialize the ComputeNode only after this event."""

    EVENT_NAME: ClassVar[EventName] = EventName.COMPUTE_READY
    event_name: Literal[EventName.COMPUTE_READY] = EventName.COMPUTE_READY

    compute_worker_id: uuid.UUID
    world_id: Optional[uuid.UUID] = None
    resource_class: ResourceClass
    region: str
    provider: ComputeProvider
    provider_instance_id: str
    cost_per_hour_usd: float = Field(..., ge=0)


class ComputeReleasedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.COMPUTE_RELEASED
    event_name: Literal[EventName.COMPUTE_RELEASED] = EventName.COMPUTE_RELEASED

    compute_worker_id: uuid.UUID
    total_cost_usd: float = Field(..., ge=0)
    reason: str


__all__ = [
    "ComputeRequestedV1",
    "ComputeProvisioningV1",
    "ComputeReadyV1",
    "ComputeReleasedV1",
]
