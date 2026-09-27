"""Payloads for the agent.* events."""

from __future__ import annotations

import uuid
from typing import ClassVar, Literal, Optional

from ghostrange_contracts.enums import AgentType
from pydantic import Field

from ._base import GhostRangeEvent
from .names import EventName


class AgentStartedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.AGENT_STARTED
    event_name: Literal[EventName.AGENT_STARTED] = EventName.AGENT_STARTED

    agent_id: uuid.UUID
    world_id: uuid.UUID
    agent_type: AgentType
    task_id: Optional[uuid.UUID] = None


class AgentActionV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.AGENT_ACTION
    event_name: Literal[EventName.AGENT_ACTION] = EventName.AGENT_ACTION

    agent_id: uuid.UUID
    world_id: uuid.UUID
    task_id: Optional[uuid.UUID] = None
    action_type: str = Field(..., description="e.g. 'shell_command', 'file_read', 'attack_technique'")
    target: Optional[str] = Field(default=None, description="e.g. hostname or asset id acted on")


class AgentCompletedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.AGENT_COMPLETED
    event_name: Literal[EventName.AGENT_COMPLETED] = EventName.AGENT_COMPLETED

    agent_id: uuid.UUID
    world_id: uuid.UUID
    task_id: Optional[uuid.UUID] = None
    outcome: str


__all__ = ["AgentStartedV1", "AgentActionV1", "AgentCompletedV1"]
