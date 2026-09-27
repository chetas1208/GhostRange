"""Verification and Observation: the middle links of the evidence chain.

Chain (see docs/architecture/EVIDENCE.md for the full narrative):

    CLAIM -> VERIFICATION -> OBSERVATION -> EXECUTION -> WORLD -> ARTIFACT

A Verification is an attempt (by an adversarial attack, static analysis,
re-execution, or peer review) to check whether a Claim holds. It is built
from one or more Observations — discrete, timestamped facts noticed during
an ExecutionRecord (``execution_graph.py``).
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import ObservationType, VerificationMethod, VerificationResult


class ObservationV1(VersionedModel):
    """A single discrete fact noticed during an ExecutionRecord.

    ``raw_artifact_id`` points at the Artifact (if any) that materializes
    the raw evidence for this observation (a log line, a pcap, a file
    diff); an observation may also be a direct agent assertion with no
    backing artifact, in which case it is None but ``summary`` still
    carries the claim-relevant fact.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    execution_id: Id = Field(..., description="ExecutionRecordV1.id this observation came from")
    world_id: Id
    agent_id: Id
    observation_type: ObservationType
    summary: str
    raw_artifact_id: Optional[Id] = None
    observed_at: AwareDatetime = Field(default_factory=utc_now)


class VerificationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    claim_id: Id
    world_id: Id
    method: VerificationMethod
    verifier_agent_id: Id
    observation_ids: list[Id] = Field(default_factory=list)
    result: VerificationResult = VerificationResult.PENDING
    reason: Optional[str] = None
    started_at: AwareDatetime = Field(default_factory=utc_now)
    completed_at: Optional[AwareDatetime] = None


__all__ = ["ObservationV1", "VerificationV1"]
