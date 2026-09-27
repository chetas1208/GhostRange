"""Payload for evidence.created."""

from __future__ import annotations

import uuid
from typing import ClassVar, Literal

from pydantic import Field

from ._base import GhostRangeEvent
from .names import EventName


class EvidenceCreatedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.EVIDENCE_CREATED
    event_name: Literal[EventName.EVIDENCE_CREATED] = EventName.EVIDENCE_CREATED

    evidence_id: uuid.UUID
    world_id: uuid.UUID
    claim_id: uuid.UUID
    verification_id: uuid.UUID
    artifact_ids: list[uuid.UUID] = Field(default_factory=list)
    content_hash: str = Field(..., description="SHA-256 hex digest, matches EvidenceV1.content_hash")


__all__ = ["EvidenceCreatedV1"]
