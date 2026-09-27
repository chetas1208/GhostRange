"""Payloads for the task.* events (Task lifecycle, including speculation).

``TaskCreatedV1``/``TaskCancelledV1`` are M2 additions (see
docs/milestones/M2_COORDINATION.md's gap list): M1 started the observable
Task lifecycle at ``task.queued`` (already implying scheduler involvement)
and had no event for ``TaskStatus.CANCELLED`` (an enum member that already
existed in ``ghostrange_contracts.enums`` with no corresponding event).
``task.created`` narrates the Task record's own creation, one step before
it is queued for scheduling; this is purely additive, ``task.queued`` is
unchanged.
"""

from __future__ import annotations

import uuid
from typing import ClassVar, Literal, Optional

from ghostrange_contracts.enums import ResourceClass, TaskType
from pydantic import Field

from ._base import GhostRangeEvent
from .names import EventName


class TaskCreatedV1(GhostRangeEvent):
    """The Task record itself was persisted (``TaskV1`` row created),
    before it is necessarily queued for scheduling. Distinct from
    ``task.queued``, which implies the scheduler has taken notice and
    assigned/confirmed a priority.
    """

    EVENT_NAME: ClassVar[EventName] = EventName.TASK_CREATED
    event_name: Literal[EventName.TASK_CREATED] = EventName.TASK_CREATED

    task_id: uuid.UUID
    world_id: uuid.UUID
    task_type: TaskType
    created_by: str = Field(..., description="agent id, or 'scheduler'")
    dependencies: list[uuid.UUID] = Field(default_factory=list)


class TaskQueuedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.TASK_QUEUED
    event_name: Literal[EventName.TASK_QUEUED] = EventName.TASK_QUEUED

    task_id: uuid.UUID
    world_id: uuid.UUID
    task_type: TaskType
    priority: int


class TaskScheduledV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.TASK_SCHEDULED
    event_name: Literal[EventName.TASK_SCHEDULED] = EventName.TASK_SCHEDULED

    task_id: uuid.UUID
    world_id: uuid.UUID
    decision_id: uuid.UUID = Field(..., description="SchedulerDecisionV1.id that scheduled this")
    target_resource_class: ResourceClass


class TaskStartedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.TASK_STARTED
    event_name: Literal[EventName.TASK_STARTED] = EventName.TASK_STARTED

    task_id: uuid.UUID
    world_id: uuid.UUID
    agent_id: Optional[uuid.UUID] = None
    compute_worker_id: Optional[uuid.UUID] = None


class TaskCompletedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.TASK_COMPLETED
    event_name: Literal[EventName.TASK_COMPLETED] = EventName.TASK_COMPLETED

    task_id: uuid.UUID
    world_id: uuid.UUID
    duration_seconds: float = Field(..., ge=0)
    actual_cost_usd: float = Field(..., ge=0)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class TaskFailedV1(GhostRangeEvent):
    EVENT_NAME: ClassVar[EventName] = EventName.TASK_FAILED
    event_name: Literal[EventName.TASK_FAILED] = EventName.TASK_FAILED

    task_id: uuid.UUID
    world_id: uuid.UUID
    error_message: str
    retry_count: int = Field(..., ge=0)
    will_retry: bool


class TaskSpeculatedV1(GhostRangeEvent):
    """Announces that a speculative branch of ``parent_task_id`` was started
    ahead of full dependency confirmation, per the Speculation policy.
    """

    EVENT_NAME: ClassVar[EventName] = EventName.TASK_SPECULATED
    event_name: Literal[EventName.TASK_SPECULATED] = EventName.TASK_SPECULATED

    task_id: uuid.UUID
    parent_task_id: uuid.UUID
    world_id: uuid.UUID
    speculative_branch_index: int = Field(..., ge=0)
    reason: str


class TaskCancelledV1(GhostRangeEvent):
    """Corresponds to ``TaskStatus.CANCELLED`` (already present in
    ``ghostrange_contracts.enums`` since M1, with no event to date).
    """

    EVENT_NAME: ClassVar[EventName] = EventName.TASK_CANCELLED
    event_name: Literal[EventName.TASK_CANCELLED] = EventName.TASK_CANCELLED

    task_id: uuid.UUID
    world_id: uuid.UUID
    reason: str
    cancelled_by: str = Field(..., description="agent id, 'scheduler', or a human identifier")


__all__ = [
    "TaskCreatedV1",
    "TaskQueuedV1",
    "TaskScheduledV1",
    "TaskStartedV1",
    "TaskCompletedV1",
    "TaskFailedV1",
    "TaskSpeculatedV1",
    "TaskCancelledV1",
]
