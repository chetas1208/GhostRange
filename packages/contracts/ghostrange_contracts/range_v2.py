"""M5: RangeSpecV2 — compiled range spec with provenance pointers."""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .range import AssetSpecV1, NetworkSpecV1


class RangeSpecV2(VersionedModel):
    """Extends RangeSpecV1 semantics with compiler provenance (additive schema)."""

    SCHEMA_VERSION: ClassVar[str] = "2"
    schema_version: Literal["2"] = "2"

    id: Id = Field(default_factory=new_id)
    name: str
    description: str = ""
    owner: str
    networks: list[NetworkSpecV1] = Field(default_factory=list)
    assets: list[AssetSpecV1] = Field(default_factory=list)
    policy_id: Optional[Id] = None
    budget_id: Optional[Id] = None
    tags: dict[str, str] = Field(default_factory=dict)
    twin_blueprint_id: Id
    placement_plan_id: Id
    compilation_manifest_id: Id
    source_graph_hash: Optional[str] = None
    compiled_from_revision: str = "1"
    created_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = ["RangeSpecV2"]
