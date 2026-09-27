"""ghostrange_events: event name vocabulary + versioned payload schemas for
GhostRange's Redis/Valkey pub-sub bus (Decisions.md #4).

Backend orchestration packages publish these; the frontend 3D visualization
consumes them and must not materialize UI state ahead of the event that
authorizes it (e.g. a ComputeNode only after ``compute.ready``, a World
node only after ``world.ready``).
"""

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
from .registry import EVENT_REGISTRY, AnyEvent, parse_event
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

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "EventName",
    "EVENT_REGISTRY",
    "AnyEvent",
    "parse_event",
    "RangeRequestedV1",
    "RangeValidatedV1",
    "RangeAuthorizedV1",
    "WorldRequestedV1",
    "WorldProvisioningV1",
    "WorldReadyV1",
    "WorldForkedV1",
    "WorldDestroyingV1",
    "WorldDestroyedV1",
    "TaskCreatedV1",
    "TaskQueuedV1",
    "TaskScheduledV1",
    "TaskStartedV1",
    "TaskCompletedV1",
    "TaskFailedV1",
    "TaskSpeculatedV1",
    "TaskCancelledV1",
    "ExecutionRequestedV1",
    "ExecutionAuthorizedV1",
    "ExecutionDeniedV1",
    "ExecutionStartedV1",
    "ExecutionCompletedV1",
    "AgentStartedV1",
    "AgentActionV1",
    "AgentCompletedV1",
    "EvidenceCreatedV1",
    "VerificationStartedV1",
    "VerificationPassedV1",
    "VerificationFailedV1",
    "ComputeRequestedV1",
    "ComputeProvisioningV1",
    "ComputeReadyV1",
    "ComputeReleasedV1",
    "SchedulerDecisionV1Event",
]
