"""Range and RangeSpec: the top-level authorized environment.

A ``RangeSpec`` is the declarative input ("what to build"); a ``Range`` is
the runtime record of an actual attempt to build and run that spec,
including its authoritative lifecycle state.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, GhostRangeModel, Id, VersionedModel, new_id, utc_now
from .enums import AssetRole, RangeLifecycleState, SecurityCriticality

# ---------------------------------------------------------------------------
# Lifecycle state machine
# ---------------------------------------------------------------------------

# Explicit transition table. This is the single source of truth for what
# transitions are legal; packages/execution-graph and the policy-check
# service enforce this at runtime rather than re-deriving their own copy.
RANGE_LIFECYCLE_TRANSITIONS: dict[RangeLifecycleState, frozenset[RangeLifecycleState]] = {
    RangeLifecycleState.REQUESTED: frozenset(
        {RangeLifecycleState.PLANNING, RangeLifecycleState.FAILED}
    ),
    RangeLifecycleState.PLANNING: frozenset(
        {RangeLifecycleState.PROVISIONING, RangeLifecycleState.FAILED}
    ),
    RangeLifecycleState.PROVISIONING: frozenset(
        {RangeLifecycleState.BOOTING, RangeLifecycleState.FAILED}
    ),
    RangeLifecycleState.BOOTING: frozenset(
        {RangeLifecycleState.READY, RangeLifecycleState.FAILED}
    ),
    RangeLifecycleState.READY: frozenset(
        {
            RangeLifecycleState.EXECUTING,
            RangeLifecycleState.STOPPING,
            RangeLifecycleState.FAILED,
        }
    ),
    RangeLifecycleState.EXECUTING: frozenset(
        {
            RangeLifecycleState.VERIFYING,
            RangeLifecycleState.STOPPING,
            RangeLifecycleState.FAILED,
        }
    ),
    RangeLifecycleState.VERIFYING: frozenset(
        {
            RangeLifecycleState.EXECUTING,  # another round of remediation/attack
            RangeLifecycleState.STOPPING,
            RangeLifecycleState.FAILED,
        }
    ),
    RangeLifecycleState.STOPPING: frozenset(
        {RangeLifecycleState.DESTROYING, RangeLifecycleState.FAILED}
    ),
    RangeLifecycleState.DESTROYING: frozenset(
        {RangeLifecycleState.DESTROYED, RangeLifecycleState.FAILED}
    ),
    RangeLifecycleState.DESTROYED: frozenset(),
    RangeLifecycleState.FAILED: frozenset(),
}

TERMINAL_RANGE_STATES: frozenset[RangeLifecycleState] = frozenset(
    {RangeLifecycleState.DESTROYED, RangeLifecycleState.FAILED}
)


def can_transition(current: RangeLifecycleState, target: RangeLifecycleState) -> bool:
    """Return whether ``current -> target`` is a legal Range transition."""
    return target in RANGE_LIFECYCLE_TRANSITIONS.get(current, frozenset())


def assert_transition(current: RangeLifecycleState, target: RangeLifecycleState) -> None:
    """Raise ``ValueError`` if ``current -> target`` is not a legal transition.

    Callers (e.g. the range-runtime reconciler) should call this before
    persisting a state change rather than trusting the caller's intent.
    """
    if not can_transition(current, target):
        raise ValueError(
            f"illegal Range transition: {current.value} -> {target.value}"
        )


# ---------------------------------------------------------------------------
# RangeSpec: declarative input
# ---------------------------------------------------------------------------


class NetworkSpecV1(GhostRangeModel):
    """A network segment to provision as part of a RangeSpec."""

    id: Id = Field(default_factory=new_id)
    name: str
    cidr: str
    vlan_id: Optional[int] = None
    description: str = ""


class AssetSpecV1(GhostRangeModel):
    """Declarative description of an asset to provision (see also asset.py's
    runtime ``AssetV1``, which is the materialized instance inside a World).
    """

    id: Id = Field(default_factory=new_id)
    hostname: str
    network_id: Id
    os_family: str
    role: AssetRole
    image: str
    criticality: SecurityCriticality = SecurityCriticality.MEDIUM


class RangeSpecV1(VersionedModel):
    """Declarative, versioned specification for a Range.

    This is the compile target for IaC (``packages/range-iac``): a
    RangeSpec is turned into OpenTofu + cloud-init inputs. It never carries
    live infrastructure state (see ``RangeV1`` for that).
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    name: str
    description: str = ""
    owner: str = Field(..., description="Email or identifier of the authorizing owner")
    networks: list[NetworkSpecV1] = Field(default_factory=list)
    assets: list[AssetSpecV1] = Field(default_factory=list)
    policy_id: Optional[Id] = None
    budget_id: Optional[Id] = None
    tags: dict[str, str] = Field(default_factory=dict)
    created_at: AwareDatetime = Field(default_factory=utc_now)


# ---------------------------------------------------------------------------
# Range: runtime record
# ---------------------------------------------------------------------------


class RangeV1(VersionedModel):
    """Runtime record of a Range: the authoritative lifecycle state plus
    pointers to the spec it was built from and the worlds forked inside it.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    spec_id: Id
    spec_version: str = "1"
    status: RangeLifecycleState = RangeLifecycleState.REQUESTED
    world_ids: list[Id] = Field(default_factory=list)
    root_world_id: Optional[Id] = None
    failure_reason: Optional[str] = None
    created_at: AwareDatetime = Field(default_factory=utc_now)
    updated_at: AwareDatetime = Field(default_factory=utc_now)
    destroyed_at: Optional[AwareDatetime] = None


__all__ = [
    "RANGE_LIFECYCLE_TRANSITIONS",
    "TERMINAL_RANGE_STATES",
    "can_transition",
    "assert_transition",
    "NetworkSpecV1",
    "AssetSpecV1",
    "RangeSpecV1",
    "RangeV1",
]
