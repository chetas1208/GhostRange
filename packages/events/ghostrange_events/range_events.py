"""Payloads for the range.* events: the front of the pipeline, before a
Range has a root World at all.

M2 gap (docs/milestones/M2_COORDINATION.md): M1's ``packages/events`` had no
``range.*`` namespace — every existing event assumed a World already
existed. M2's pipeline (RangeSpec -> validation -> policy gate ->
range-runtime -> provider) needs to be observable before that point, so the
UI can show "your Range was received / is being checked / was authorized to
provision" before any World node could possibly exist. These three events
are purely additive: no existing event is renamed or removed.

Relationship to ``RangeLifecycleState`` (``ghostrange_contracts.range``):
these are finer-grained *pipeline* events that all occur logically within
the ``REQUESTED -> PLANNING`` transition of the authoritative Range state
machine; they do not add new states to that machine, they narrate what
happens inside it.
"""

from __future__ import annotations

import uuid
from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import GhostRangeEvent
from .names import EventName


class RangeRequestedV1(GhostRangeEvent):
    """A RangeSpec was submitted and a Range record created for it
    (``RangeV1.status == REQUESTED``). Analogous to ``world.requested`` but
    one level up the hierarchy.
    """

    EVENT_NAME: ClassVar[EventName] = EventName.RANGE_REQUESTED
    event_name: Literal[EventName.RANGE_REQUESTED] = EventName.RANGE_REQUESTED

    range_id: uuid.UUID
    spec_id: uuid.UUID
    spec_version: str = "1"
    requested_by: str = Field(..., description="Email or identifier of the authorizing owner")


class RangeValidatedV1(GhostRangeEvent):
    """Structural/semantic validation of the RangeSpec (shape, referenced
    ids resolve, no orphan network/asset refs) completed. Carries the
    outcome directly (``valid``) rather than splitting into a separate
    pass/fail event pair, mirroring ``world.destroyed``'s optional-reason
    pattern: one event, an outcome field, because the UI's "next" action
    (proceed to authorization, or stop) is the same regardless of which
    branch fired it.
    """

    EVENT_NAME: ClassVar[EventName] = EventName.RANGE_VALIDATED
    event_name: Literal[EventName.RANGE_VALIDATED] = EventName.RANGE_VALIDATED

    range_id: uuid.UUID
    spec_id: uuid.UUID
    valid: bool
    validation_errors: list[str] = Field(default_factory=list)


class RangeAuthorizedV1(GhostRangeEvent):
    """Policy + Budget attached and authorization granted to proceed to
    provisioning (the concrete condition ``PRODUCT.md`` §3 lists for
    ``REQUESTED -> PLANNING``). Only fired on a positive outcome — there is
    deliberately no ``range.denied``/``range.rejected`` in this M2 slice
    (not requested by ``M2_COORDINATION.md``'s gap list); a Range that
    fails authorization stays observable via the existing Range lifecycle
    (``RangeLifecycleState.FAILED``) once ``apps/api`` emits that
    transition, which is out of scope for this package.
    """

    EVENT_NAME: ClassVar[EventName] = EventName.RANGE_AUTHORIZED
    event_name: Literal[EventName.RANGE_AUTHORIZED] = EventName.RANGE_AUTHORIZED

    range_id: uuid.UUID
    spec_id: uuid.UUID
    policy_id: uuid.UUID
    budget_id: uuid.UUID
    authorized_by: str = Field(..., description="Human identifier, or 'auto-policy'")
    root_world_id: Optional[uuid.UUID] = Field(
        default=None, description="Set once the root World id is known/reserved"
    )


__all__ = ["RangeRequestedV1", "RangeValidatedV1", "RangeAuthorizedV1"]
