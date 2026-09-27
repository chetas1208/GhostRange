"""Hypothesis, Remediation, AttackAttempt: the investigation/remediation/
adversarial-verification triad that drives World forking.

A Hypothesis is what an investigator agent proposes about root cause or
risk. A Remediation is a candidate fix for a Hypothesis, applied inside its
own forked World. An AttackAttempt is the adversary agent's attempt to
break a Remediation, inside that same World — its outcome feeds a
Verification (see ``verification.py``).
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, Id, VersionedModel, new_id, utc_now
from .enums import AttackOutcome, HypothesisStatus


class HypothesisV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    statement: str
    confidence: float = Field(..., ge=0, le=1)
    status: HypothesisStatus = HypothesisStatus.OPEN
    supporting_evidence_ids: list[Id] = Field(default_factory=list)
    proposed_by_agent_id: Id
    created_at: AwareDatetime = Field(default_factory=utc_now)


class RemediationV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    hypothesis_id: Optional[Id] = None
    description: str
    actions: list[str] = Field(default_factory=list, description="Ordered remediation steps taken")
    applied_by_agent_id: Id
    applied_at: Optional[AwareDatetime] = None
    created_at: AwareDatetime = Field(default_factory=utc_now)


class AttackAttemptV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    world_id: Id
    remediation_id: Optional[Id] = Field(
        default=None, description="Remediation being attacked, if this is a post-fix re-attack"
    )
    technique_id: str = Field(..., description="MITRE ATT&CK technique id, e.g. T1059.001")
    technique_name: str
    outcome: AttackOutcome = AttackOutcome.INCONCLUSIVE
    executed_by_agent_id: Id
    evidence_ids: list[Id] = Field(default_factory=list)
    executed_at: AwareDatetime = Field(default_factory=utc_now)


__all__ = ["HypothesisV1", "RemediationV1", "AttackAttemptV1"]
