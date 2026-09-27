"""World and WorldFork: the "cyber multiverse" branching model.

A ``World`` is one concrete, running instantiation of (part of) a Range's
assets — the unit that gets forked when GhostRange wants to try two
competing remediations in parallel. A ``WorldFork`` is the immutable record
of one such branching event: it is what the frontend's 3D multiverse view
replays to draw the fork tree, and it is deliberately a first-class,
queryable object (not just inferrable from ``World.parent_world_id``)
because "why did we fork here" is itself evidence-relevant.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import WorldStatus


class WorldV1(VersionedModel):
    """One node in the multiverse tree: a running (or terminated) branch."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    range_id: Id
    parent_world_id: Optional[Id] = Field(
        default=None, description="None iff this is the root World of its Range"
    )
    label: str = Field(..., description="Human-readable branch label, e.g. 'remediation-a'")
    status: WorldStatus = WorldStatus.REQUESTED
    hypothesis_id: Optional[Id] = None
    created_at: AwareDatetime = Field(default_factory=utc_now)
    destroyed_at: Optional[AwareDatetime] = None
    failure_reason: Optional[str] = None


class WorldForkV1(VersionedModel):
    """Immutable record of a World forking into a new child World.

    ``fork_reason`` is free text for humans; if a caller wants a
    machine-readable reason it should additionally reference a
    ``SchedulerDecisionV1`` (e.g. via a ``BRANCH_LOW_VALUE``-style code) —
    forks driven by the scheduler carry their decision id in
    ``triggered_by_decision_id``.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    range_id: Id
    parent_world_id: Id
    child_world_id: Id
    fork_reason: str
    triggered_by_decision_id: Optional[Id] = None
    created_by: str = Field(..., description="Agent id or 'scheduler' or a human identifier")
    created_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = ["WorldV1", "WorldForkV1"]
