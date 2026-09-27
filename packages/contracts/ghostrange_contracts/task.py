"""Task and its supporting value objects: ResourceProfile, RetryPolicy,
SpeculationPolicy.

A Task is the unit of work GhostScheduler schedules. Its fields are the
scheduler's entire input signal — anything the scheduler needs to weigh
cost against expected evidence gain must be a field here, not tribal
knowledge encoded in scheduler code.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field, field_validator

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import ResourceClass, SecurityCriticality, TaskStatus, TaskType


class ResourceProfileV1(VersionedModel):
    """What a Task asks for, before the scheduler decides what it gets.

    Compare to ``SchedulerDecisionV1.target_resource_class`` (what it
    actually gets) and ``ComputeWorkerV1.resource_class`` (what got
    provisioned) — three points where a mismatch is meaningful telemetry.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    cpu_cores: float = Field(..., gt=0)
    memory_gb: float = Field(..., gt=0)
    gpu_required: bool = False
    gpu_type: Optional[str] = None
    preferred_resource_class: Optional[ResourceClass] = None

    @field_validator("gpu_type")
    @classmethod
    def _gpu_type_requires_gpu(cls, v: Optional[str], info):
        if v is not None and not info.data.get("gpu_required", False):
            raise ValueError("gpu_type set but gpu_required is False")
        return v


class RetryPolicyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    max_retries: int = Field(default=0, ge=0, le=20)
    backoff_seconds: float = Field(default=5.0, ge=0)
    retry_on_reason_codes: list[str] = Field(default_factory=list)


class SpeculationPolicyV1(VersionedModel):
    """Governs whether/how this Task may be run speculatively (started
    before its full dependency chain is confirmed valuable) per the
    Speculative Execution research track.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    enabled: bool = False
    max_speculative_branches: int = Field(default=1, ge=0, le=16)
    cancel_on_primary_success: bool = True


class TaskV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    task_type: TaskType
    dependencies: list[Id] = Field(
        default_factory=list, description="Task ids that must complete before this one starts"
    )
    resource_profile: ResourceProfileV1
    estimated_duration_seconds: float = Field(..., ge=0)
    estimated_cost_usd: float = Field(..., ge=0)
    priority: int = Field(default=0, description="Higher runs first, ties broken by scheduler")
    security_criticality: SecurityCriticality = SecurityCriticality.MEDIUM
    uncertainty: float = Field(
        ..., ge=0, le=1, description="Scheduler's estimate of outcome uncertainty, 0=certain"
    )
    expected_evidence_gain: float = Field(
        ..., ge=0, description="Scheduler's estimate of evidentiary value if run"
    )
    retry_policy: RetryPolicyV1 = Field(default_factory=RetryPolicyV1)
    speculation_policy: SpeculationPolicyV1 = Field(default_factory=SpeculationPolicyV1)
    status: TaskStatus = TaskStatus.QUEUED
    created_at: AwareDatetime = Field(default_factory=utc_now)
    updated_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = [
    "ResourceProfileV1",
    "RetryPolicyV1",
    "SpeculationPolicyV1",
    "TaskV1",
]
