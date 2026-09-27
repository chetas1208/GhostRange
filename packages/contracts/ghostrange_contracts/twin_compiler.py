"""M5: Twin blueprint, placement, compilation manifest, compiler state."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .fidelity_m5 import FidelityProfileV1


class CompilerState(str, Enum):
    RECEIVED = "RECEIVED"
    PARSING = "PARSING"
    NORMALIZING = "NORMALIZING"
    MERGING = "MERGING"
    SANITIZING = "SANITIZING"
    RESOLVING = "RESOLVING"
    FIDELITY_PLANNING = "FIDELITY_PLANNING"
    PLACING = "PLACING"
    COMPILING = "COMPILING"
    VALIDATING_PLAN = "VALIDATING_PLAN"
    PROVISIONING = "PROVISIONING"
    BOOTING = "BOOTING"
    VALIDATING_TWIN = "VALIDATING_TWIN"
    READY = "READY"
    FAILED = "FAILED"
    DESTROYING = "DESTROYING"
    DESTROYED = "DESTROYED"


class SanitizationPolicyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    reject_plaintext_secrets: bool = True
    default_external_dependency: str = "STUB"
    default_data_replica: str = "SYNTHETIC"
    deny_internet_egress: bool = True
    startup_script_mode: str = "INSPECT"


class DataReplicaPolicyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    strategy: str = Field(default="SYNTHETIC", description="EMPTY_SCHEMA|SYNTHETIC|FIXTURE|SCHEMA_ONLY|AUTHORIZED_SNAPSHOT")


class TwinSecretSubstitutionV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    original_reference: str
    replacement_type: str
    twin_secret_ref: str


class TwinBlueprintV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    revision: str = Field(default="1")
    ghost_ir_id: Id
    fidelity_profile_id: Id
    logical_topology_summary: str = ""
    required_services: list[str] = Field(default_factory=list)
    service_images: dict[str, str] = Field(default_factory=dict)
    network_policies: list[str] = Field(default_factory=list)
    secret_substitutions: list[TwinSecretSubstitutionV1] = Field(default_factory=list)
    external_stubs: list[str] = Field(default_factory=list)
    resource_requirements: dict[str, str] = Field(default_factory=dict)
    required_invariant_ids: list[Id] = Field(default_factory=list)
    blueprint_hash: Optional[str] = None
    created_at: AwareDatetime = Field(default_factory=utc_now)


class PlacementAlternativeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    label: str
    vm_count: int = Field(..., ge=1)
    estimated_hourly_cost_usd: float = Field(..., ge=0)
    resource_fidelity_score: float = Field(..., ge=0, le=1)
    explanation: str


class PlacementPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    blueprint_id: Id
    selected_vm_count: int = Field(..., ge=1)
    asset_to_vm: dict[str, str] = Field(default_factory=dict)
    alternatives: list[PlacementAlternativeV1] = Field(default_factory=list)
    estimated_build_seconds: float = Field(default=0, ge=0)
    estimated_startup_seconds: float = Field(default=0, ge=0)
    estimated_hourly_cost_usd: float = Field(default=0, ge=0)
    placement_hash: Optional[str] = None
    explanation: Optional[str] = None


class TemplateFingerprintV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    fingerprint: str
    base_image: str
    bootstrap_version: str
    network_profile: str
    service_bundle_hash: str
    resource_class: str


class VultrDeploymentPlanV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    placement_plan_id: Id
    template_fingerprints: list[TemplateFingerprintV1] = Field(default_factory=list)
    snapshot_ids: list[str] = Field(default_factory=list)
    compiled_infra_ref: Optional[str] = Field(
        default=None, description="Pointer to range-iac CompiledRangeInfra blob"
    )


class CompilationManifestV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    compilation_id: Id = Field(default_factory=new_id)
    source_hashes: list[str] = Field(default_factory=list)
    parser_versions: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    normalization_decisions: list[str] = Field(default_factory=list)
    sanitization_decisions: list[str] = Field(default_factory=list)
    substitutions: list[str] = Field(default_factory=list)
    placement_decisions: list[str] = Field(default_factory=list)
    template_ids: list[str] = Field(default_factory=list)
    snapshot_ids: list[str] = Field(default_factory=list)
    fidelity_profile: Optional[FidelityProfileV1] = None
    compiler_version: str = "range-compiler/v0.1"
    policy_version: str = "sanitization/v1"
    blueprint_hash: Optional[str] = None
    created_at: AwareDatetime = Field(default_factory=utc_now)


class TwinBudgetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    max_cost_usd: float = Field(..., gt=0)
    max_compile_seconds: float = Field(default=600, gt=0)
    min_fidelity_profile_id: Optional[Id] = None


__all__ = [
    "CompilerState",
    "SanitizationPolicyV1",
    "DataReplicaPolicyV1",
    "TwinSecretSubstitutionV1",
    "TwinBlueprintV1",
    "PlacementAlternativeV1",
    "PlacementPlanV1",
    "TemplateFingerprintV1",
    "VultrDeploymentPlanV1",
    "CompilationManifestV1",
    "TwinBudgetV1",
]
