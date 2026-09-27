"""M5: GhostIR — compiler intermediate representation between graph and blueprint."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class GhostIRNodeKind(str, Enum):
    LOGICAL_SERVICE = "LOGICAL_SERVICE"
    COMPUTE_ASSET = "COMPUTE_ASSET"
    NETWORK_SEGMENT = "NETWORK_SEGMENT"
    DATA_STORE = "DATA_STORE"
    EXTERNAL_STUB = "EXTERNAL_STUB"
    IDENTITY_BOUNDARY = "IDENTITY_BOUNDARY"


class GhostIRV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    normalized_graph_id: Id
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    compiler_version: str = "range-compiler/v0.1"
    ir_hash: Optional[str] = None
    created_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = ["GhostIRNodeKind", "GhostIRV1"]
