"""Payloads for the execution.* events: the policy-gated dispatch of one
concrete run of a Task.

M2 gap (docs/milestones/M2_COORDINATION.md): M1 modeled a Task's own
lifecycle (``task.queued/scheduled/started/completed/failed``) but had no
event trail for the safety-boundary check ``PRODUCT.md`` §2.9/§5 invariant
#1 requires before every dispatch ("no Task or AttackAttempt may target an
Asset not in the owning Range's active Policy.asset_allowlist ... must hold
even if the Agent is compromised"). These five events make that check
itself observable and auditable, distinct from (and narrower than) the
Task-level events: an ``execution.*`` sequence corresponds to one
``ExecutionRecordV1`` (``ghostrange_contracts.execution_graph``) — one
concrete attempt to run a Task, which may be retried as a new
ExecutionRecord/execution_id under the same task_id.

Ordering for one execution attempt: requested -> (authorized | denied) ->
[if authorized] started -> completed. ``denied`` is terminal for that
attempt; a retry is a new ``execution_id``.
"""

from __future__ import annotations

import uuid
from typing import ClassVar, Literal, Optional

from ghostrange_contracts.enums import ExecutionStatus
from pydantic import Field

from ._base import GhostRangeEvent
from .names import EventName


class ExecutionRequestedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.EXECUTION_REQUESTED
    event_name: Literal[EventName.EXECUTION_REQUESTED] = EventName.EXECUTION_REQUESTED

    execution_id: uuid.UUID
    task_id: uuid.UUID
    world_id: uuid.UUID
    requested_by: str = Field(..., description="agent id, or 'scheduler'")
    target_asset_ids: list[uuid.UUID] = Field(default_factory=list)


class ExecutionAuthorizedV1(GhostRangeEvent):
    """The policy-check enforcement point (``packages/execution-graph``,
    Decisions.md #9) approved dispatch: every id in ``target_asset_ids``
    was confirmed present in the Range's active Policy allowlist.
    """

    EVENT_NAME: ClassVar[EventName] = EventName.EXECUTION_AUTHORIZED
    event_name: Literal[EventName.EXECUTION_AUTHORIZED] = EventName.EXECUTION_AUTHORIZED

    execution_id: uuid.UUID
    task_id: uuid.UUID
    world_id: uuid.UUID
    policy_id: uuid.UUID
    target_asset_ids: list[uuid.UUID] = Field(default_factory=list)


class ExecutionDeniedV1(GhostRangeEvent):
    """The policy-check enforcement point rejected dispatch. This is the
    literal, machine-checkable evidence trail for ``PRODUCT.md``'s "no
    override code path" invariant — every denial that ever happens is a
    durable, replayable row, not just a raised exception in a log line.
    """

    EVENT_NAME: ClassVar[EventName] = EventName.EXECUTION_DENIED
    event_name: Literal[EventName.EXECUTION_DENIED] = EventName.EXECUTION_DENIED

    execution_id: uuid.UUID
    task_id: uuid.UUID
    world_id: uuid.UUID
    policy_id: uuid.UUID
    reason: str
    offending_asset_ids: list[uuid.UUID] = Field(
        default_factory=list, description="target_asset_ids not present in the allowlist"
    )


class ExecutionStartedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.EXECUTION_STARTED
    event_name: Literal[EventName.EXECUTION_STARTED] = EventName.EXECUTION_STARTED

    execution_id: uuid.UUID
    task_id: uuid.UUID
    world_id: uuid.UUID
    agent_id: Optional[uuid.UUID] = None
    compute_worker_id: Optional[uuid.UUID] = None
    command: Optional[str] = None


class ExecutionCompletedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.EXECUTION_COMPLETED
    event_name: Literal[EventName.EXECUTION_COMPLETED] = EventName.EXECUTION_COMPLETED

    execution_id: uuid.UUID
    task_id: uuid.UUID
    world_id: uuid.UUID
    status: ExecutionStatus
    exit_code: Optional[int] = None
    duration_seconds: float = Field(..., ge=0)
    artifact_ids: list[uuid.UUID] = Field(default_factory=list)


__all__ = [
    "ExecutionRequestedV1",
    "ExecutionAuthorizedV1",
    "ExecutionDeniedV1",
    "ExecutionStartedV1",
    "ExecutionCompletedV1",
]
