"""Claim, Evidence, Artifact: the ends of the provenance chain.

    CLAIM -> VERIFICATION -> OBSERVATION -> EXECUTION -> WORLD -> ARTIFACT

A Claim is an assertion an agent puts forward ("this remediation closes
CVE-XXXX-YYYY"). It accumulates Verifications. An Evidence record bundles
together the Verification result plus the Observations and Artifacts that
back it, into the thing that actually gets shown to a human or downstream
agent as "why we believe this". Artifacts are the leaf nodes: concrete
content-addressed bytes (a log file, a pcap, a screenshot) stored in
object storage, referenced by hash for tamper-evidence.
"""

from __future__ import annotations

import re
from typing import ClassVar, Literal, Optional

from pydantic import Field, field_validator

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import ArtifactType, HashAlgorithm

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class ArtifactV1(VersionedModel):
    """A concrete, content-addressed piece of evidence data.

    ``content_hash`` is the hex digest of the artifact's bytes under
    ``hash_algorithm`` (SHA-256 by default) and is what makes provenance
    tamper-evident: two Artifacts with the same hash are the same bytes,
    full stop, regardless of which World or execution produced them.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    produced_by_execution_id: Optional[Id] = None
    artifact_type: ArtifactType
    storage_uri: str = Field(..., description="e.g. vultr-object-storage://bucket/key")
    hash_algorithm: HashAlgorithm = HashAlgorithm.SHA256
    content_hash: str
    size_bytes: int = Field(..., ge=0)
    created_at: AwareDatetime = Field(default_factory=utc_now)

    @field_validator("content_hash")
    @classmethod
    def _validate_hash_format(cls, v: str, info) -> str:
        algo = info.data.get("hash_algorithm", HashAlgorithm.SHA256)
        if algo == HashAlgorithm.SHA256 and not _SHA256_HEX_RE.match(v.lower()):
            raise ValueError(
                f"content_hash '{v}' is not a valid lowercase 64-char SHA-256 hex digest"
            )
        return v.lower()


class ClaimV1(VersionedModel):
    """An assertion made by an agent, subject to verification."""

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    statement: str
    made_by_agent_id: Id
    confidence: float = Field(..., ge=0, le=1)
    verification_ids: list[Id] = Field(default_factory=list)
    created_at: AwareDatetime = Field(default_factory=utc_now)


class EvidenceV1(VersionedModel):
    """A bundle tying a Claim's Verification to the Observations and
    Artifacts that back it — the object surfaced to humans/UI as the
    "proof" behind a conclusion, and what ``evidence.created`` announces.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    claim_id: Id
    verification_id: Id
    observation_ids: list[Id] = Field(..., min_length=1)
    artifact_ids: list[Id] = Field(default_factory=list)
    summary: str
    content_hash: str = Field(
        ..., description="SHA-256 hex digest summarizing this evidence bundle for provenance chaining"
    )
    created_at: AwareDatetime = Field(default_factory=utc_now)

    @field_validator("content_hash")
    @classmethod
    def _validate_hash_format(cls, v: str) -> str:
        if not _SHA256_HEX_RE.match(v.lower()):
            raise ValueError(
                f"content_hash '{v}' is not a valid lowercase 64-char SHA-256 hex digest"
            )
        return v.lower()


__all__ = ["ArtifactV1", "ClaimV1", "EvidenceV1"]
