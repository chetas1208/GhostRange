"""Investigation intake — the minimum input contract for starting a
GhostRange investigation from a GitHub repository + plain-English incident
description.

Product direction (see ``docs/architecture/PRODUCT.md``): a GitHub
repository URL + a plain-English incident description should be enough to
start an investigation. This is the first thing a user gives the system,
before any ``RangeSpec`` exists.

Pipeline this feeds (see ``docs/architecture/RANGE_COMPILER.md``):
``InvestigationIntakeV1`` -> (repo acquisition + heuristic scan, see
``ghostrange_range_compiler.intake``) -> ``DerivedSystemModelV1`` ->
(future, out of scope here) RangeSpec compilation.

Runtime evidence (logs/traces) is explicitly out of scope for this pass;
``evidence`` is accepted and passed through unopinionated for a future
evidence pipeline (see ``docs/architecture/EVIDENCE.md``) to consume.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from ._base import AwareDatetime, VersionedModel


class IncidentDescriptorV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    title: str
    description: str
    observed_at: Optional[AwareDatetime] = None


class SystemSourceRefV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    repository_url: str
    branch: str = "main"


class InvestigationConstraintsV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    max_workers: int = Field(default=1, ge=1)
    max_cost_usd: float = Field(default=1.0, ge=0)
    live_production_actions: bool = False


class InvestigationIntakeV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    case_id: str
    incident: IncidentDescriptorV1
    system: SystemSourceRefV1
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    constraints: InvestigationConstraintsV1 = Field(default_factory=InvestigationConstraintsV1)


__all__ = [
    "IncidentDescriptorV1",
    "SystemSourceRefV1",
    "InvestigationConstraintsV1",
    "InvestigationIntakeV1",
]
