"""Payloads for verification.* events."""

from __future__ import annotations

import uuid
from typing import ClassVar, Literal

from ghostrange_contracts.enums import VerificationMethod
from pydantic import Field

from ._base import GhostRangeEvent
from .names import EventName


class VerificationStartedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.VERIFICATION_STARTED
    event_name: Literal[EventName.VERIFICATION_STARTED] = EventName.VERIFICATION_STARTED

    verification_id: uuid.UUID
    claim_id: uuid.UUID
    world_id: uuid.UUID
    method: VerificationMethod
    verifier_agent_id: uuid.UUID


class VerificationPassedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.VERIFICATION_PASSED
    event_name: Literal[EventName.VERIFICATION_PASSED] = EventName.VERIFICATION_PASSED

    verification_id: uuid.UUID
    claim_id: uuid.UUID
    world_id: uuid.UUID
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class VerificationFailedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.VERIFICATION_FAILED
    event_name: Literal[EventName.VERIFICATION_FAILED] = EventName.VERIFICATION_FAILED

    verification_id: uuid.UUID
    claim_id: uuid.UUID
    world_id: uuid.UUID
    reason: str


__all__ = ["VerificationStartedV1", "VerificationPassedV1", "VerificationFailedV1"]
