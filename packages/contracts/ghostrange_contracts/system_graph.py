"""M5: NormalizedSystemGraph — single convergence model for all importers."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class GraphNodeKind(str, Enum):
    HOST = "HOST"
    VM = "VM"
    CONTAINER = "CONTAINER"
    POD = "POD"
    SERVICE = "SERVICE"
    DATABASE = "DATABASE"
    QUEUE = "QUEUE"
    CACHE = "CACHE"
    OBJECT_STORE = "OBJECT_STORE"
    GATEWAY = "GATEWAY"
    LOAD_BALANCER = "LOAD_BALANCER"
    IDENTITY_PROVIDER = "IDENTITY_PROVIDER"
    VOLUME = "VOLUME"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    NETWORK = "NETWORK"
    SUBNET = "SUBNET"
    SECRET_REFERENCE = "SECRET_REFERENCE"


class GraphEdgeKind(str, Enum):
    HOSTS = "HOSTS"
    CONNECTS_TO = "CONNECTS_TO"
    DEPENDS_ON = "DEPENDS_ON"
    AUTHENTICATES_VIA = "AUTHENTICATES_VIA"
    READS_FROM = "READS_FROM"
    WRITES_TO = "WRITES_TO"
    EXPOSES = "EXPOSES"
    ROUTES_TO = "ROUTES_TO"
    MOUNTS = "MOUNTS"
    CONSUMES_SECRET = "CONSUMES_SECRET"
    MEMBER_OF_NETWORK = "MEMBER_OF_NETWORK"


class SourceProvenanceV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    source_file: str
    source_construct: str
    source_location: str
    parser_id: str


class NormalizedNodeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    name: str
    kind: GraphNodeKind
    labels: dict[str, str] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    provenance: SourceProvenanceV1
    provider_metadata: dict[str, str] = Field(default_factory=dict)


class NormalizedEdgeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    from_node_id: Id
    to_node_id: Id
    kind: GraphEdgeKind
    attributes: dict[str, str] = Field(default_factory=dict)
    provenance: SourceProvenanceV1


class SourceConflictV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    conflict_id: Id = Field(default_factory=new_id)
    subject: str
    description: str
    source_a: str
    source_b: str
    resolution_hint: Optional[str] = None


class NormalizedSystemGraphV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    source_model_ids: list[Id] = Field(default_factory=list)
    nodes: list[NormalizedNodeV1] = Field(default_factory=list)
    edges: list[NormalizedEdgeV1] = Field(default_factory=list)
    conflicts: list[SourceConflictV1] = Field(default_factory=list)
    graph_hash: Optional[str] = None
    created_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = [
    "GraphNodeKind",
    "GraphEdgeKind",
    "SourceProvenanceV1",
    "NormalizedNodeV1",
    "NormalizedEdgeV1",
    "SourceConflictV1",
    "NormalizedSystemGraphV1",
]
