"""M5: Fidelity profiles, reports, invariants, observations."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class FidelityDimension(str, Enum):
    TOPOLOGY = "TOPOLOGY"
    NETWORK = "NETWORK"
    SERVICE = "SERVICE"
    CONFIGURATION = "CONFIGURATION"
    VERSION = "VERSION"
    IDENTITY = "IDENTITY"
    DATA_SCHEMA = "DATA_SCHEMA"
    DATA_CONTENT = "DATA_CONTENT"
    RUNTIME_BEHAVIOR = "RUNTIME_BEHAVIOR"
    RESOURCE = "RESOURCE"
    STORAGE = "STORAGE"
    TIMING = "TIMING"
    DEPENDENCY = "DEPENDENCY"
    SECURITY_CONTROL = "SECURITY_CONTROL"


class FidelityRequirementLevel(str, Enum):
    REQUIRED = "REQUIRED"
    IMPORTANT = "IMPORTANT"
    OPTIONAL = "OPTIONAL"
    IGNORED = "IGNORED"


class FidelityDimensionStatus(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_MEASURED = "NOT_MEASURED"


class InvestigationObjectiveV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    title: str
    description: str
    investigation_kind: str = Field(
        default="auth_remediation",
        description="Rule-map key, e.g. auth_remediation, gpu_isolation",
    )


class FidelityProfileV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    objective_id: Id
    dimensions: dict[FidelityDimension, FidelityRequirementLevel] = Field(default_factory=dict)
    pass_threshold: float = Field(default=0.85, ge=0, le=1)


class BehavioralInvariantV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    name: str
    description: str
    check_kind: str
    target_node_name: Optional[str] = None
    parameters: dict[str, str] = Field(default_factory=dict)
    mandatory: bool = True


class InvariantComparisonStatus(str, Enum):
    MATCH = "MATCH"
    FUNCTIONALLY_EQUIVALENT = "FUNCTIONALLY_EQUIVALENT"
    MISMATCH = "MISMATCH"
    NOT_MEASURED = "NOT_MEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SourceObservationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    invariant_id: Id
    observed_value: str
    captured_at: AwareDatetime = Field(default_factory=utc_now)
    authorized: bool = True


class TwinObservationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    invariant_id: Id
    observed_value: str
    world_id: Id
    captured_at: AwareDatetime = Field(default_factory=utc_now)


class InvariantComparisonV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    invariant_id: Id
    status: InvariantComparisonStatus
    notes: Optional[str] = None


class FidelityDimensionScoreV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    dimension: FidelityDimension
    requirement: FidelityRequirementLevel
    score: Optional[float] = Field(default=None, ge=0, le=1)
    status: FidelityDimensionStatus


class FidelityReportV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    objective_id: Id
    dimensions: list[FidelityDimensionScoreV1] = Field(default_factory=list)
    invariants: list[InvariantComparisonV1] = Field(default_factory=list)
    substitutions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    unsupported_constructs: list[str] = Field(default_factory=list)
    valid_for_investigation: bool = False
    failure_reason: Optional[str] = None
    created_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = [
    "FidelityDimension",
    "FidelityRequirementLevel",
    "FidelityDimensionStatus",
    "InvestigationObjectiveV1",
    "FidelityProfileV1",
    "BehavioralInvariantV1",
    "InvariantComparisonStatus",
    "SourceObservationV1",
    "TwinObservationV1",
    "InvariantComparisonV1",
    "FidelityDimensionScoreV1",
    "FidelityReportV1",
]
