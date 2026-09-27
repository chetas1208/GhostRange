"""Record types for the GhostRange <-> NetBird control-plane boundary.

These are intentionally a thin, faithful shape of NetBird's own management
API responses (see https://docs.netbird.io/api), not GhostRange's domain
vocabulary — callers (``apps/api``'s worker readiness gate) translate
between the two layers.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PeerGroupRef(BaseModel):
    """A group as embedded in a peer's own ``groups`` list — NetBird's
    ``/api/peers`` response nests {id, name, ...} directly, so no separate
    id->name resolution call is needed to check group membership."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str


class Peer(BaseModel):
    """One NetBird peer (an enrolled machine on the mesh)."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str = Field(default="", description="Peer's display name — defaults to the enrolling machine's hostname.")
    hostname: str = Field(default="")
    ip: Optional[str] = None
    connected: bool = False
    last_seen: Optional[str] = None
    groups: list[PeerGroupRef] = Field(default_factory=list)
    ssh_enabled: bool = False
    raw: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw NetBird response fields, for debugging/audit. Never contains the API token.",
    )

    @property
    def group_names(self) -> set[str]:
        return {g.name for g in self.groups}

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Peer":
        groups = [PeerGroupRef(id=g.get("id", ""), name=g.get("name", "")) for g in data.get("groups") or []]
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            hostname=str(data.get("hostname", "")),
            ip=data.get("ip"),
            connected=bool(data.get("connected", False)),
            last_seen=data.get("last_seen"),
            groups=groups,
            ssh_enabled=bool(data.get("ssh_enabled", False)),
            raw=data,
        )


class Group(BaseModel):
    """One NetBird policy group."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    peers_count: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Group":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            peers_count=int(data.get("peers_count", 0) or 0),
            raw=data,
        )


class SetupKey(BaseModel):
    """A NetBird setup key, as returned right after creation (this is the
    only time the plaintext ``key`` is ever returned by NetBird's API)."""

    model_config = ConfigDict(extra="allow")

    id: str
    key: str = Field(default="", description="Plaintext setup key. Only present on the create response.")
    name: str = ""
    type: str = "reusable"
    expires_at: Optional[str] = None
    auto_groups: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "SetupKey":
        return cls(
            id=str(data.get("id", "")),
            key=str(data.get("key", "")),
            name=str(data.get("name", "")),
            type=str(data.get("type", "reusable")),
            expires_at=data.get("expires_at"),
            auto_groups=list(data.get("auto_groups") or []),
            raw=data,
        )


__all__ = ["Peer", "PeerGroupRef", "Group", "SetupKey"]
