"""M5: SourceModel — preserve imported artifacts before semantic normalization."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class SourceType(str, Enum):
    DOCKER_COMPOSE = "docker_compose"
    TERRAFORM = "terraform"
    OPENTOFU = "opentofu"
    TERRAFORM_PLAN_JSON = "terraform_plan_json"
    KUBERNETES = "kubernetes"
    GHOSTRANGE_BLUEPRINT = "ghostrange_blueprint"
    INVENTORY_JSON = "inventory_json"


class UnsupportedConstructStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    APPROXIMATED = "APPROXIMATED"
    STUBBED = "STUBBED"
    IGNORED_OPTIONAL = "IGNORED_OPTIONAL"
    UNSUPPORTED_REQUIRED = "UNSUPPORTED_REQUIRED"


class SourceFileRefV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    path: str
    content_hash: str
    byte_size: int = Field(..., ge=0)


class SourceResourceRecordV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    construct_type: str
    construct_name: str
    source_location: str = Field(..., description="file:line or AST path")
    raw_attributes: dict[str, Any] = Field(default_factory=dict)
    secret_reference_only: bool = False


class SourceWarningV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    code: str
    message: str
    source_location: Optional[str] = None
    status: UnsupportedConstructStatus = UnsupportedConstructStatus.APPROXIMATED


class SourceModelV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    source_type: SourceType
    source_version: Optional[str] = None
    files: list[SourceFileRefV1] = Field(default_factory=list)
    resources: list[SourceResourceRecordV1] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    networks: list[str] = Field(default_factory=list)
    volumes: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    variables: dict[str, str] = Field(default_factory=dict)
    secrets_references: list[str] = Field(
        default_factory=list, description="Names/paths only — never secret values"
    )
    configuration_references: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    warnings: list[SourceWarningV1] = Field(default_factory=list)
    parser_id: str
    parser_version: str
    created_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = [
    "SourceType",
    "UnsupportedConstructStatus",
    "SourceFileRefV1",
    "SourceResourceRecordV1",
    "SourceWarningV1",
    "SourceModelV1",
]
