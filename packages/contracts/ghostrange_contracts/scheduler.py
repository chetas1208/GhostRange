"""SchedulerDecision: GhostScheduler's atomic unit of output.

Every time GhostScheduler decides what compute runs where/when/how long for
a Task (or a branch), it emits exactly one ``SchedulerDecisionV1``. This is
also the payload embedded in the ``scheduler.decision`` event
(``packages/events``), so the frontend's execution-graph visualization and
this record are always describing the same object.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import ReasonCode, ResourceClass


class SchedulerDecisionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    task_id: Id
    world_id: Id
    target_resource_class: ResourceClass
    priority: int
    estimated_cost_usd: float = Field(..., ge=0)
    expected_value: float = Field(
        ..., description="Scheduler's unitless expected-evidence-value score for this decision"
    )
    parallelism: int = Field(default=1, ge=1)
    speculative: bool = False
    reason_codes: list[ReasonCode] = Field(
        ..., min_length=1, description="Machine-readable justification; never empty"
    )
    constraints: dict[str, str] = Field(
        default_factory=dict,
        description="Free-form key/value scheduling constraints, e.g. {'region': 'ewr'}",
    )
    expiration: AwareDatetime = Field(
        ..., description="This decision is stale and must be re-evaluated after this time"
    )
    termination_condition: str = Field(
        ..., description="Human/agent-readable condition under which the allocation is released"
    )
    notes: Optional[str] = Field(default=None, description="Free-text context, never a substitute for reason_codes")
    created_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = ["SchedulerDecisionV1"]
