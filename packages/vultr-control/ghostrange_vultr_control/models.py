"""Request/response record types for the GhostRange <-> Vultr control-plane
boundary.

Design notes
------------
These types are intentionally *not* the same models as
``ghostrange_contracts`` (``WorldV1``, ``ComputeWorkerV1``, ...). This package
sits one layer below the domain contracts: it speaks the shape of Vultr's
actual API (or a faithful mock of it), not GhostRange's domain vocabulary.
``packages/range-runtime`` / ``packages/range-iac`` are expected to translate
between the two layers (e.g. ``WorldV1.id`` -> ``CreateWorldRequest.tags.world_id``
as a plain string) rather than this package importing ``ghostrange_contracts``
directly. That keeps this package's dependency graph shallow and lets it be
used standalone (unit tests, a throwaway script) without pulling in the whole
contracts stack.

Every record produced by either provider implementation carries a
``provider`` field (``ProviderKind.VULTR`` or ``ProviderKind.MOCK``) so a
caller — or a test, or evidence/audit tooling — can never mistake a mock
resource for a real, billable one.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProviderKind(str, Enum):
    """Which implementation produced a record. Never inferred, always set
    explicitly by the provider that created the record."""

    VULTR = "vultr"
    MOCK = "mock"


class ResourceStatus(str, Enum):
    """Provider-agnostic lifecycle status for a world or compute resource.

    Deliberately coarser than Vultr's own instance ``status`` /
    ``power_status`` / ``server_status`` triad (see ``ComputeRecord.raw`` and
    the ``vultr_power_status``/``vultr_server_status`` fields for the raw
    values) — this is the status callers should branch on; the raw fields are
    for debugging/finer-grained readiness checks only.
    """

    PENDING = "pending"
    ACTIVE = "active"
    DELETING = "deleting"
    DELETED = "deleted"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Ownership metadata / tagging
# ---------------------------------------------------------------------------

_TAG_NAMESPACE = "ghostrange"


class GhostRangeTags(BaseModel):
    """Ownership metadata GhostRange stamps on every Vultr resource it
    creates, needed later for orphan detection (find + reap resources whose
    owning Range/World no longer exists, or whose ttl has elapsed).

    Vultr tagging reality check (verified against the current `govultr` v3
    Go SDK source, which mirrors the live API v2 request/response schema,
    2026-09-26):

    - Compute instances accept a flat ``tags`` array of **opaque strings** —
      there is no native key/value tag structure
      (``InstanceCreateReq.Tags []string``). We encode
      ``ghostrange:<key>:<value>`` strings and parse them back out.
    - VPCs and Firewall Groups do **not** accept a `tags` field at all — the
      only free-text field available on either is ``description``
      (``VPCReq.Description``, ``FirewallGroupReq.Description``). We encode
      the same metadata into ``description`` for those resource types.

    This is a real, documented limitation of Vultr's API, not a gap in this
    package: orphan-detection for a World (VPC) can only key off
    ``description`` text, not a structured tag list.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    range_id: str = Field(..., min_length=1)
    world_id: Optional[str] = None
    created_by: str = "ghostrange"
    ttl_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description=(
            "Advisory time-to-live in seconds from creation. Not enforced by "
            "Vultr itself (Vultr has no native TTL/expiry on these resource "
            "types) — an orphan-reaper job compares created_at + ttl_seconds "
            "to now."
        ),
    )

    def as_vultr_tag_list(self) -> list[str]:
        """Render as Vultr's flat tag-string list for instance creation."""
        tags = [
            f"{_TAG_NAMESPACE}:created_by:{self.created_by}",
            f"{_TAG_NAMESPACE}:range_id:{self.range_id}",
        ]
        if self.world_id is not None:
            tags.append(f"{_TAG_NAMESPACE}:world_id:{self.world_id}")
        if self.ttl_seconds is not None:
            tags.append(f"{_TAG_NAMESPACE}:ttl_seconds:{self.ttl_seconds}")
        return tags

    def as_description(self) -> str:
        """Render as a ``description`` string for VPC/Firewall Group create."""
        parts = [f"created_by={self.created_by}", f"range_id={self.range_id}"]
        if self.world_id is not None:
            parts.append(f"world_id={self.world_id}")
        if self.ttl_seconds is not None:
            parts.append(f"ttl_seconds={self.ttl_seconds}")
        return f"{_TAG_NAMESPACE};" + ";".join(parts)

    @classmethod
    def from_vultr_tag_list(cls, tags: list[str]) -> Optional["GhostRangeTags"]:
        """Parse GhostRange ownership metadata back out of an instance's raw
        ``tags`` list. Returns ``None`` (never a fabricated/default record)
        if the resource carries no GhostRange tags — e.g. it was not created
        by GhostRange, or a required field (``range_id``) is missing.
        """
        prefix = f"{_TAG_NAMESPACE}:"
        found: dict[str, str] = {}
        for tag in tags:
            if not tag.startswith(prefix):
                continue
            rest = tag[len(prefix) :]
            key, _, value = rest.partition(":")
            if key:
                found[key] = value
        if "range_id" not in found:
            return None
        ttl_raw = found.get("ttl_seconds")
        return cls(
            range_id=found["range_id"],
            world_id=found.get("world_id"),
            created_by=found.get("created_by", "ghostrange"),
            ttl_seconds=int(ttl_raw) if ttl_raw is not None and ttl_raw.isdigit() else None,
        )

    @classmethod
    def from_description(cls, description: Optional[str]) -> Optional["GhostRangeTags"]:
        """Parse GhostRange ownership metadata back out of a VPC/Firewall
        Group's ``description`` field. Returns ``None`` if it isn't a
        GhostRange-owned description (e.g. hand-created resource, or a
        different tool's convention).
        """
        if not description or not description.startswith(f"{_TAG_NAMESPACE};"):
            return None
        body = description[len(f"{_TAG_NAMESPACE};") :]
        found: dict[str, str] = {}
        for part in body.split(";"):
            key, sep, value = part.partition("=")
            if sep:
                found[key] = value
        if "range_id" not in found:
            return None
        ttl_raw = found.get("ttl_seconds")
        return cls(
            range_id=found["range_id"],
            world_id=found.get("world_id"),
            created_by=found.get("created_by", "ghostrange"),
            ttl_seconds=int(ttl_raw) if ttl_raw is not None and ttl_raw.isdigit() else None,
        )


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class CreateWorldRequest(BaseModel):
    """Create one GhostRange "World" isolation unit: one Vultr VPC, per
    ADR-006's "one VPC 2.0 per world" decision, optionally paired with a
    dedicated Firewall Group for that world's intra-world traffic policy.
    """

    model_config = ConfigDict(extra="forbid")

    region: str = Field(..., min_length=1)
    tags: GhostRangeTags
    v4_subnet: Optional[str] = None
    v4_subnet_mask: Optional[int] = Field(default=None, ge=0, le=32)
    create_firewall_group: bool = True


class CreateComputeRequest(BaseModel):
    """Create one range asset: a Vultr Compute instance attached to a
    World's VPC. Mirrors ADR-006's field mapping table 1:1 (see this
    package's README for the exact Vultr request field each of these
    becomes).
    """

    model_config = ConfigDict(extra="forbid")

    world_ref: str = Field(..., min_length=1, description="provider_world_id from create_world()")
    region: str = Field(..., min_length=1)
    plan: str = Field(..., min_length=1)
    tags: GhostRangeTags
    os_id: Optional[int] = Field(default=None, description="Base image to boot fresh (materialize-a-base-world path)")
    snapshot_id: Optional[str] = Field(default=None, description="Restore from a pre-warmed golden snapshot (fork path)")
    script_id: Optional[str] = None
    user_data: Optional[str] = Field(default=None, description="Raw cloud-config text (this package base64-encodes it before sending)")
    firewall_group_id: Optional[str] = None
    hostname: Optional[str] = None
    label: Optional[str] = None
    enable_ipv6: bool = False
    backups: bool = False

    @model_validator(mode="after")
    def _exactly_one_boot_source(self) -> "CreateComputeRequest":
        if bool(self.os_id) == bool(self.snapshot_id):
            raise ValueError(
                "CreateComputeRequest requires exactly one of os_id (fresh build) or "
                "snapshot_id (fork restore), per ADR-006's two compilation modes — "
                f"got os_id={self.os_id!r} snapshot_id={self.snapshot_id!r}"
            )
        return self


# ---------------------------------------------------------------------------
# Records (results)
# ---------------------------------------------------------------------------


class WorldRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderKind
    provider_world_id: str
    firewall_group_id: Optional[str] = None
    region: str
    v4_subnet: Optional[str] = None
    v4_subnet_mask: Optional[int] = None
    status: ResourceStatus
    tags: Optional[GhostRangeTags] = Field(
        default=None,
        description="None means this resource carries no parseable GhostRange ownership metadata (never fabricated).",
    )
    created_at: datetime = Field(default_factory=utc_now)
    raw: dict[str, Any] = Field(default_factory=dict, description="Raw provider response fields, for debugging/audit. Never contains the API key.")


class ComputeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderKind
    provider_compute_id: str
    world_ref: Optional[str] = Field(default=None, description="provider_world_id this compute is attached to, if known")
    region: str
    plan: str
    label: Optional[str] = None
    hostname: Optional[str] = None
    main_ip: Optional[str] = None
    status: ResourceStatus
    vultr_power_status: Optional[str] = Field(default=None, description="Raw Vultr power_status ('running'/'stopped'/...), informational only")
    vultr_server_status: Optional[str] = Field(default=None, description="Raw Vultr server_status ('ok'/'none'/...), informational only")
    tags: Optional[GhostRangeTags] = None
    created_at: datetime = Field(default_factory=utc_now)
    raw: dict[str, Any] = Field(default_factory=dict, description="Raw provider response fields, for debugging/audit. Never contains the API key.")


__all__ = [
    "ProviderKind",
    "ResourceStatus",
    "GhostRangeTags",
    "CreateWorldRequest",
    "CreateComputeRequest",
    "WorldRecord",
    "ComputeRecord",
]
