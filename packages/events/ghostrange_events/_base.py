"""Shared base class for every GhostRange event payload.

Every event is a single flat Pydantic model published as one Redis
pub-sub message: the envelope fields (``event_id``, ``event_name``,
``occurred_at``, ``schema_version``) plus the event-specific fields, all in
one JSON object. This is deliberately not a generic ``Envelope[Payload]``
wrapper — a flat shape means every consumer (backend orchestration,
frontend 3D visualization) can pattern-match on ``event_name`` and read
fields directly, with no unwrapping step.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import ClassVar

from ghostrange_contracts._base import GhostRangeModel
from pydantic import AwareDatetime, Field

from .names import EventName


def new_event_id() -> uuid.UUID:
    return uuid.uuid4()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GhostRangeEvent(GhostRangeModel):
    """Base class for all event payloads.

    Subclasses MUST override ``EVENT_NAME`` (a ``ClassVar``) and declare a
    matching ``event_name: Literal[EventName.X] = EventName.X`` field, so
    the discriminated union in ``registry.py`` can dispatch on it and the
    serialized JSON is self-describing.
    """

    EVENT_NAME: ClassVar[EventName]

    event_id: uuid.UUID = Field(default_factory=new_event_id)
    occurred_at: AwareDatetime = Field(default_factory=utc_now)
    schema_version: str = "1"


__all__ = ["GhostRangeEvent", "new_event_id", "utc_now"]
