"""Agent: an autonomous actor (investigator, remediator, adversary, verifier,
or orchestrator) operating inside a World.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import AgentStatus, AgentType


class AgentV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    agent_type: AgentType
    status: AgentStatus = AgentStatus.STARTED
    model_identifier: Optional[str] = Field(
        default=None, description="e.g. 'claude-sonnet-5' — which model/policy drives this agent"
    )
    current_task_id: Optional[Id] = None
    created_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = ["AgentV1"]
