"""ExecutionGraph: the DAG of Tasks for a World, plus ExecutionRecord, the
provenance record of one actual run of a Task.

``packages/execution-graph`` owns the algorithms (topological scheduling,
critical path, cycle detection, the safety-boundary enforcement point); this
module only owns the *shape* of the data those algorithms operate on, so
every package agrees on it.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field, model_validator

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import ExecutionStatus


class DependencyEdgeV1(VersionedModel):
    """A directed edge ``upstream_task_id -> downstream_task_id`` meaning
    downstream depends on upstream having completed.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    upstream_task_id: Id
    downstream_task_id: Id

    @model_validator(mode="after")
    def _no_self_loop(self) -> "DependencyEdgeV1":
        if self.upstream_task_id == self.downstream_task_id:
            raise ValueError("a task cannot depend on itself")
        return self


class ExecutionGraphV1(VersionedModel):
    """The DAG of Tasks for one World. Cycle-freedom is NOT validated here
    (that requires graph traversal, which belongs in
    ``packages/execution-graph`` where it can be tested against the real
    scheduling algorithms) — this model only guarantees shape, not
    acyclicity.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    task_ids: list[Id] = Field(default_factory=list)
    edges: list[DependencyEdgeV1] = Field(default_factory=list)
    created_at: AwareDatetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _edges_reference_known_tasks(self) -> "ExecutionGraphV1":
        known = set(self.task_ids)
        for edge in self.edges:
            if edge.upstream_task_id not in known or edge.downstream_task_id not in known:
                raise ValueError(
                    f"edge {edge.upstream_task_id}->{edge.downstream_task_id} "
                    "references a task_id not present in task_ids"
                )
        return self


class ExecutionRecordV1(VersionedModel):
    """Provenance record of one concrete execution of a Task: this is the
    EXECUTION node in the Claim -> Verification -> Observation -> Execution
    -> World -> Artifact evidence chain (see docs/architecture/EVIDENCE.md).
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    task_id: Id
    world_id: Id
    agent_id: Optional[Id] = None
    compute_worker_id: Optional[Id] = None
    command: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.RUNNING
    exit_code: Optional[int] = None
    artifact_ids: list[Id] = Field(default_factory=list)
    started_at: AwareDatetime = Field(default_factory=utc_now)
    completed_at: Optional[AwareDatetime] = None


__all__ = ["DependencyEdgeV1", "ExecutionGraphV1", "ExecutionRecordV1"]
