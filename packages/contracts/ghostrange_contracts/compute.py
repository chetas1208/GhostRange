"""ComputeWorker: an actual provisioned unit of compute (a Vultr instance,
or a local mock in dev) that Tasks execute on.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import ComputeProvider, ComputeWorkerStatus, ResourceClass


class ComputeWorkerV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    resource_class: ResourceClass
    provider: ComputeProvider = ComputeProvider.VULTR
    status: ComputeWorkerStatus = ComputeWorkerStatus.REQUESTED
    region: str
    provider_instance_id: Optional[str] = Field(
        default=None, description="Vultr instance id once provisioned; None until then"
    )
    cost_per_hour_usd: float = Field(..., ge=0)
    world_id: Optional[Id] = Field(
        default=None, description="World this worker is currently bound to, if any"
    )
    created_at: AwareDatetime = Field(default_factory=utc_now)
    ready_at: Optional[AwareDatetime] = None
    released_at: Optional[AwareDatetime] = None


__all__ = ["ComputeWorkerV1"]
