"""Payload for scheduler.decision.

This mirrors ``SchedulerDecisionV1`` from ``ghostrange_contracts.scheduler``
field-for-field (plus the event envelope) rather than embedding that model
as a nested object, so every event on the bus stays a single flat JSON
object consumers can pattern-match without an unwrapping step (see
``_base.py`` docstring).
"""

from __future__ import annotations

import uuid
from typing import ClassVar, Literal

from ghostrange_contracts.enums import ReasonCode, ResourceClass
from pydantic import AwareDatetime, Field

from ._base import GhostRangeEvent
from .names import EventName


class SchedulerDecisionV1Event(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.SCHEDULER_DECISION
    event_name: Literal[EventName.SCHEDULER_DECISION] = EventName.SCHEDULER_DECISION

    decision_id: uuid.UUID
    task_id: uuid.UUID
    world_id: uuid.UUID
    target_resource_class: ResourceClass
    priority: int
    estimated_cost_usd: float = Field(..., ge=0)
    expected_value: float
    parallelism: int = Field(..., ge=1)
    speculative: bool
    reason_codes: list[ReasonCode] = Field(..., min_length=1)
    expiration: AwareDatetime
    termination_condition: str


__all__ = ["SchedulerDecisionV1Event"]
