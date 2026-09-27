"""The event registry: EventName -> exactly one payload schema.

This is the module every consumer should import from to go from "a raw
dict/JSON string came off Redis" to "a validated, typed event object",
without needing to know the full list of payload classes itself.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Union

from pydantic import Field, TypeAdapter

from .agent_events import AgentActionV1, AgentCompletedV1, AgentStartedV1
from .compute_events import (
    ComputeProvisioningV1,
    ComputeReadyV1,
    ComputeReleasedV1,
    ComputeRequestedV1,
)
from .evidence_events import EvidenceCreatedV1
from .execution_events import (
    ExecutionAuthorizedV1,
    ExecutionCompletedV1,
    ExecutionDeniedV1,
    ExecutionRequestedV1,
    ExecutionStartedV1,
)
from .names import EventName
from .range_events import RangeAuthorizedV1, RangeRequestedV1, RangeValidatedV1
from .scheduler_events import SchedulerDecisionV1Event
from .task_events import (
    TaskCancelledV1,
    TaskCompletedV1,
    TaskCreatedV1,
    TaskFailedV1,
    TaskQueuedV1,
    TaskScheduledV1,
    TaskSpeculatedV1,
    TaskStartedV1,
)
from .verification_events import VerificationFailedV1, VerificationPassedV1, VerificationStartedV1
from .world_events import (
    WorldDestroyedV1,
    WorldDestroyingV1,
    WorldForkedV1,
    WorldProvisioningV1,
    WorldReadyV1,
    WorldRequestedV1,
)

# EventName -> the single payload class that owns that event name.
# Every EventName member MUST have exactly one entry here — enforced by
# tests/test_registry.py, not just by convention.
EVENT_REGISTRY: dict[EventName, type] = {
    EventName.RANGE_REQUESTED: RangeRequestedV1,
    EventName.RANGE_VALIDATED: RangeValidatedV1,
    EventName.RANGE_AUTHORIZED: RangeAuthorizedV1,
    EventName.WORLD_REQUESTED: WorldRequestedV1,
    EventName.WORLD_PROVISIONING: WorldProvisioningV1,
    EventName.WORLD_READY: WorldReadyV1,
    EventName.WORLD_FORKED: WorldForkedV1,
    EventName.WORLD_DESTROYING: WorldDestroyingV1,
    EventName.WORLD_DESTROYED: WorldDestroyedV1,
    EventName.TASK_CREATED: TaskCreatedV1,
    EventName.TASK_QUEUED: TaskQueuedV1,
    EventName.TASK_SCHEDULED: TaskScheduledV1,
    EventName.TASK_STARTED: TaskStartedV1,
    EventName.TASK_COMPLETED: TaskCompletedV1,
    EventName.TASK_FAILED: TaskFailedV1,
    EventName.TASK_SPECULATED: TaskSpeculatedV1,
    EventName.TASK_CANCELLED: TaskCancelledV1,
    EventName.EXECUTION_REQUESTED: ExecutionRequestedV1,
    EventName.EXECUTION_AUTHORIZED: ExecutionAuthorizedV1,
    EventName.EXECUTION_DENIED: ExecutionDeniedV1,
    EventName.EXECUTION_STARTED: ExecutionStartedV1,
    EventName.EXECUTION_COMPLETED: ExecutionCompletedV1,
    EventName.AGENT_STARTED: AgentStartedV1,
    EventName.AGENT_ACTION: AgentActionV1,
    EventName.AGENT_COMPLETED: AgentCompletedV1,
    EventName.EVIDENCE_CREATED: EvidenceCreatedV1,
    EventName.VERIFICATION_STARTED: VerificationStartedV1,
    EventName.VERIFICATION_PASSED: VerificationPassedV1,
    EventName.VERIFICATION_FAILED: VerificationFailedV1,
    EventName.COMPUTE_REQUESTED: ComputeRequestedV1,
    EventName.COMPUTE_PROVISIONING: ComputeProvisioningV1,
    EventName.COMPUTE_READY: ComputeReadyV1,
    EventName.COMPUTE_RELEASED: ComputeReleasedV1,
    EventName.SCHEDULER_DECISION: SchedulerDecisionV1Event,
}

# Discriminated union of every event payload, keyed on the `event_name`
# field. Useful for consumers that want "give me the right type" parsing
# via a single TypeAdapter rather than a manual if/elif chain.
AnyEvent = Annotated[
    Union[
        RangeRequestedV1,
        RangeValidatedV1,
        RangeAuthorizedV1,
        WorldRequestedV1,
        WorldProvisioningV1,
        WorldReadyV1,
        WorldForkedV1,
        WorldDestroyingV1,
        WorldDestroyedV1,
        TaskCreatedV1,
        TaskQueuedV1,
        TaskScheduledV1,
        TaskStartedV1,
        TaskCompletedV1,
        TaskFailedV1,
        TaskSpeculatedV1,
        TaskCancelledV1,
        ExecutionRequestedV1,
        ExecutionAuthorizedV1,
        ExecutionDeniedV1,
        ExecutionStartedV1,
        ExecutionCompletedV1,
        AgentStartedV1,
        AgentActionV1,
        AgentCompletedV1,
        EvidenceCreatedV1,
        VerificationStartedV1,
        VerificationPassedV1,
        VerificationFailedV1,
        ComputeRequestedV1,
        ComputeProvisioningV1,
        ComputeReadyV1,
        ComputeReleasedV1,
        SchedulerDecisionV1Event,
    ],
    Field(discriminator="event_name"),
]

_any_event_adapter: TypeAdapter[Any] = TypeAdapter(AnyEvent)


def parse_event(raw: str | bytes | dict[str, Any]) -> Any:
    """Parse a raw pub-sub message (JSON string/bytes, or an already-decoded
    dict) into its correctly typed event payload, dispatching on
    ``event_name``. Raises ``pydantic.ValidationError`` if the payload does
    not match the schema its own ``event_name`` claims — this is
    deliberate: a malformed event on the bus must fail loudly, not be
    coerced into "close enough".
    """
    if isinstance(raw, (str, bytes)):
        data = json.loads(raw)
    else:
        data = raw
    return _any_event_adapter.validate_python(data)


__all__ = ["EVENT_REGISTRY", "AnyEvent", "parse_event"]
