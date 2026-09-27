"""Derived System Model — heuristic candidate system model from a public
repository scan (GitHub-as-input feature).

Positioning relative to the M5 Range Compiler pipeline (see
``source_model.py`` and ``docs/architecture/RANGE_COMPILER.md``):
``SourceModelV1`` represents *already-authorized* IaC artifacts
(compose/Terraform/K8s) parsed precisely for the fidelity-gated
blueprint -> RangeSpec pipeline.

``DerivedSystemModelV1`` sits one step *earlier* and is intentionally
looser: given nothing but a public repository URL + branch, it
heuristically scans the tree for structural signals (compose files,
Dockerfiles, Kubernetes manifests, Terraform, package manifests,
OpenAPI specs, ``.env.example`` files) and produces a best-effort,
explicitly low-confidence candidate service inventory — the
"static/declared state" half of the Living Twin, before any human has
authorized building a Range from it.

It is upstream of, and does not replace, ``RangeSpecV1``/``RangeSpecV2``:
turning a ``DerivedSystemModelV1`` into a buildable Range is a separate,
not-yet-built step (out of scope for this contract).

Every derived fact carries a ``DerivationProvenanceV1`` so a human/agent
can audit exactly which file and heuristic produced it — matching the
evidence-provenance philosophy in ``docs/architecture/EVIDENCE.md``,
without adopting that pipeline's stricter machinery for this first pass.
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now


class DerivationSourceKind(str, Enum):
    DOCKER_COMPOSE = "docker_compose"
    DOCKERFILE = "dockerfile"
    KUBERNETES_MANIFEST = "kubernetes_manifest"
    TERRAFORM = "terraform"
    PACKAGE_MANIFEST = "package_manifest"
    OPENAPI_SPEC = "openapi_spec"
    ENV_TEMPLATE = "env_template"
    DIRECTORY_HEURISTIC = "directory_heuristic"


class DerivedServiceRole(str, Enum):
    AUTH = "auth"
    API = "api"
    GATEWAY = "gateway"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    FRONTEND = "frontend"
    WORKER = "worker"
    UNKNOWN = "unknown"


class DerivationConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"


class DerivationProvenanceV1(VersionedModel):
    """Which file + heuristic produced one derived fact.

    A derived fact with no provenance entry is treated as a bug in the
    scanner, not an acceptable edge case — see repo_scanner.py.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    source_kind: DerivationSourceKind
    source_path: str = Field(..., description="Path relative to repo root, e.g. 'docker-compose.yml'")
    locator: str = Field(..., description="Where inside the file, e.g. 'services.auth' or 'EXPOSE 8080'")
    rule: str = Field(..., description="Heuristic name that produced this fact, e.g. 'compose_service_block'")
    note: str = Field(default="", description="Human-readable explanation for audit display")


class DerivedServiceV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    name: str
    inferred_role: DerivedServiceRole = DerivedServiceRole.UNKNOWN
    role_confidence: DerivationConfidence = DerivationConfidence.LOW
    image: Optional[str] = None
    build_context: Optional[str] = None
    language: Optional[str] = None
    ports: list[int] = Field(default_factory=list)
    is_external_interface: bool = False
    provenance: list[DerivationProvenanceV1] = Field(default_factory=list)


class DerivedDependencyEdgeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    from_service: str
    to_service: str
    relationship: str = "depends_on"
    provenance: list[DerivationProvenanceV1] = Field(default_factory=list)


class RepoScanSummaryV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    files_scanned: int = Field(..., ge=0)
    files_relevant: int = Field(..., ge=0)
    services_identified: int = Field(..., ge=0)
    data_stores_identified: int = Field(..., ge=0)
    external_interfaces_identified: int = Field(..., ge=0)
    warnings: list[str] = Field(default_factory=list)

    def narration(self) -> str:
        """First-20-seconds narration string (see docs/architecture/PRODUCT.md)."""
        return (
            f"{self.files_relevant} files relevant... "
            f"{self.services_identified} services identified... "
            f"{self.data_stores_identified} data stores identified... "
            f"{self.external_interfaces_identified} external interfaces identified."
        )


class DerivedSystemModelV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    repository_url: str
    branch: str
    commit_sha: Optional[str] = None
    services: list[DerivedServiceV1] = Field(default_factory=list)
    dependency_edges: list[DerivedDependencyEdgeV1] = Field(default_factory=list)
    summary: RepoScanSummaryV1
    confidence_disclaimer: str = (
        "Heuristic, best-effort derivation from repository structure only. "
        "Not verified against runtime behavior; treat every fact as a hypothesis, not ground truth."
    )
    created_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = [
    "DerivationSourceKind",
    "DerivedServiceRole",
    "DerivationConfidence",
    "DerivationProvenanceV1",
    "DerivedServiceV1",
    "DerivedDependencyEdgeV1",
    "RepoScanSummaryV1",
    "DerivedSystemModelV1",
]
