"""Runtime materialized Network / Asset / Service inside a World.

These mirror ``NetworkSpecV1`` / ``AssetSpecV1`` from ``range.py`` but
represent the *actual provisioned thing inside a specific World*, carrying
live identifiers (IPs, Vultr resource ids) that don't exist until
provisioning has happened. Declarative spec and runtime instance are kept
as separate model families on purpose: a World can diverge from its spec
(e.g. an attacker adds a service) and that divergence is itself evidence.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import AssetRole, SecurityCriticality


class NetworkV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    name: str
    cidr: str
    vlan_id: Optional[int] = None


class AssetV1(VersionedModel):
    """A provisioned host inside a World."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    network_id: Id
    hostname: str
    os_family: str
    role: AssetRole
    ip_address: Optional[str] = None
    criticality: SecurityCriticality = SecurityCriticality.MEDIUM
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: AwareDatetime = Field(default_factory=utc_now)


class ServiceV1(VersionedModel):
    """A network service exposed by an Asset."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    asset_id: Id
    name: str
    port: int = Field(..., ge=1, le=65535)
    protocol: str = Field(..., description="e.g. tcp, udp")
    version: Optional[str] = None
    known_cves: list[str] = Field(default_factory=list)


__all__ = ["NetworkV1", "AssetV1", "ServiceV1"]
