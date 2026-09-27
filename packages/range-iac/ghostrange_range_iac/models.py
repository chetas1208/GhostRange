"""range-iac's own model family: PHYSICAL placement + network topology.

These are deliberately **not** part of ``ghostrange_contracts`` (frozen for M2 wave 1
per docs/milestones/M2_COORDINATION.md). ``RangeSpecV1`` describes a range's LOGICAL
shape only (networks, assets, roles, images) and has no notion of "which physical
Vultr instance does this asset actually run on" or "what can reach what over the
network" — see packages/contracts/ghostrange_contracts/range.py. Conflating those two
concerns into one schema is exactly the mistake docs/adr/ADR-M2-RANGE-PROVISIONING.md
argues against: GhostScheduler needs to move logical assets between physical hosts
later without ever touching the RangeSpec that describes what those assets *are*.

So: a companion, versioned-the-same-way model family lives here, one level below
range-iac's compiler. A range's physical/topology data is checked in next to its
RangeSpec, e.g. ``ranges/ghostrange-auth-lab-v1/topology.yaml``, and cross-referenced
against the RangeSpec by asset hostname (human-friendly) rather than raw UUIDs, then
resolved to real ``AssetSpecV1.id`` values by the compiler.

If/when ``packages/contracts`` grows an official placement/topology model, this module
should be retired in favor of it (propose via the M2 contract-change protocol, don't
silently duplicate) — until then this is the documented, working substitute.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from ghostrange_contracts._base import GhostRangeModel, Id, VersionedModel
from pydantic import Field, field_validator

# Sentinel used in ReachabilityEdgeV1.from_asset to mean "outside the range entirely"
# (the internet, or a test-harness origin driving traffic at the gateway). It is not a
# real asset and never resolves to a physical group.
INTERNET = "INTERNET"


class PhysicalGroupV1(GhostRangeModel):
    """One physical Vultr Compute instance and the logical assets consolidated onto it.

    For ghostrange-auth-lab-v1's M2 layout there is exactly one of these, holding all
    four logical assets. A later, less consolidated layout would have one
    PhysicalGroupV1 per asset (or per tier) — the compiler and the RangeSpec do not
    change either way, only this file does.
    """

    id: str = Field(..., description="Physical group id, e.g. 'vm-1'. Not a Vultr id.")
    asset_ids: list[Id] = Field(
        ..., min_length=1, description="AssetSpecV1.id values consolidated onto this VM"
    )
    region: str = Field(..., description="Vultr region slug, e.g. 'ewr' (Newark, NJ)")
    plan: str = Field(..., description="Vultr plan slug, e.g. 'vc2-2c-4gb'")
    os_id: Optional[int] = Field(
        default=None,
        description=(
            "Vultr base-OS image id for BASE (materialize-from-scratch) compilation. "
            "NEEDS VERIFICATION against `GET /v2/os` at provision time -- numeric os_id "
            "values are Vultr account/catalog state, not a stable public constant, and "
            "can drift. Mutually exclusive with a runtime-supplied snapshot_id (fork mode)."
        ),
    )
    default_snapshot_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional pinned Vultr snapshot id for FORK compilation of this group. "
            "Usually left null here and supplied per-fork by the caller of "
            "compile_range(..., snapshot_map=...) instead, since a golden snapshot is "
            "created out of band (20-30 min, see ADR-006) after a base world reaches "
            "steady state, not authored by hand into this file."
        ),
    )
    needs_public_ip: bool = Field(
        default=False,
        description=(
            "Whether this physical group must have a public IPv4 (i.e. it hosts at "
            "least one asset with an INTERNET-sourced reachability edge). The compiler "
            "also derives this independently from the edge list and will raise if the "
            "two disagree, so this field can't silently go stale."
        ),
    )


class ReachabilityEdgeV1(GhostRangeModel):
    """One declared 'A can reach B on port/protocol' edge in the LOGICAL topology.

    ``from_asset``/``to_asset`` are AssetSpecV1 hostnames (or the ``INTERNET`` sentinel
    for from_asset only). The compiler resolves these to physical groups and decides,
    per edge, whether it needs a real Vultr firewall rule (the two ends land on
    different physical groups, or the edge originates at INTERNET) or nothing at all
    beyond the world's own VPC 2.0 membership (both ends land on the same physical
    group -- same-host traffic, e.g. two containers on one docker-compose network,
    never touches the Vultr network fabric).
    """

    from_asset: str
    to_asset: str
    port: int = Field(..., ge=1, le=65535)
    protocol: Literal["tcp", "udp"] = "tcp"
    description: str = ""

    @field_validator("to_asset")
    @classmethod
    def _to_asset_not_internet(cls, v: str) -> str:
        if v == INTERNET:
            raise ValueError("INTERNET may only appear as from_asset, never to_asset")
        return v


class RangeTopologyPlanV1(VersionedModel):
    """The PHYSICAL placement + reachability plan for one RangeSpec.

    One of these per range, checked in as ``<range dir>/topology.yaml``. Cross-checked
    against its RangeSpecV1 at compile time (every hostname/asset_id referenced here
    must exist there, and vice versa -- every RangeSpec asset must be placed exactly
    once).
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    range_spec_id: Id = Field(..., description="Must equal the target RangeSpecV1.id")
    range_name: str
    physical_groups: list[PhysicalGroupV1] = Field(..., min_length=1)
    edges: list[ReachabilityEdgeV1] = Field(default_factory=list)


__all__ = [
    "INTERNET",
    "PhysicalGroupV1",
    "ReachabilityEdgeV1",
    "RangeTopologyPlanV1",
]
