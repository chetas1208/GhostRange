"""EventName: the fixed vocabulary of GhostRange events.

Every event published to Redis/Valkey pub-sub (per Decisions.md #4) carries
one of these names as its ``event_name`` discriminator field. The registry
in ``registry.py`` maps each name to exactly one payload schema — see that
module's docstring and ``tests/test_registry.py`` for the invariant this
enforces.
"""

from __future__ import annotations

from enum import Enum


class EventName(str, Enum):
    # Range lifecycle (M2 addition — see docs/milestones/M2_COORDINATION.md;
    # additive only, no existing member renamed/removed)
    RANGE_REQUESTED = "range.requested"
    RANGE_VALIDATED = "range.validated"
    RANGE_AUTHORIZED = "range.authorized"

    # World lifecycle
    WORLD_REQUESTED = "world.requested"
    WORLD_PROVISIONING = "world.provisioning"
    WORLD_READY = "world.ready"
    WORLD_FORKED = "world.forked"
    WORLD_DESTROYING = "world.destroying"
    WORLD_DESTROYED = "world.destroyed"

    # Task lifecycle
    TASK_CREATED = "task.created"  # M2 addition
    TASK_QUEUED = "task.queued"
    TASK_SCHEDULED = "task.scheduled"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_SPECULATED = "task.speculated"
    TASK_CANCELLED = "task.cancelled"  # M2 addition

    # Execution (policy-gated dispatch of one Task run; M2 addition)
    EXECUTION_REQUESTED = "execution.requested"
    EXECUTION_AUTHORIZED = "execution.authorized"
    EXECUTION_DENIED = "execution.denied"
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"

    # Agent lifecycle
    AGENT_STARTED = "agent.started"
    AGENT_ACTION = "agent.action"
    AGENT_COMPLETED = "agent.completed"

    # Evidence
    EVIDENCE_CREATED = "evidence.created"

    # Verification
    VERIFICATION_STARTED = "verification.started"
    VERIFICATION_PASSED = "verification.passed"
    VERIFICATION_FAILED = "verification.failed"

    # Compute
    COMPUTE_REQUESTED = "compute.requested"
    COMPUTE_PROVISIONING = "compute.provisioning"
    COMPUTE_READY = "compute.ready"
    COMPUTE_RELEASED = "compute.released"

    # Scheduler
    SCHEDULER_DECISION = "scheduler.decision"


__all__ = ["EventName"]
