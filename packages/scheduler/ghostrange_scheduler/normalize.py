"""Normalization layer: the single highest-priority fix identified in
``ADAPTIVE_COMPUTE.md`` §4.1.4 ("No normalization contract stated for any
factor... this is arguably the single most urgent, cheapest-to-fix issue").

``NormalizedPriorityFactorsV1`` is the enforced-[0,1] boundary the doc asks
for, implemented as a real Pydantic model with ``@field_validator``s per
its explicit recommendation (§4.3): "recommend this becomes a Pydantic
validator... constraining these four fields to [0.0, 1.0] at the schema
level, so it's structurally impossible for a producer to emit an
out-of-range value rather than relying on convention."

Why this lives in ``packages/scheduler`` and not ``packages/contracts``:
the ideal long-term fix is upstream, on ``TaskV1`` itself (bound
``expected_evidence_gain`` to [0,1], and add first-class
``security_risk``/``dependency_criticality`` fields) -- but ``TaskV1`` is
frozen for M2 wave 1 and shared by many agents, so that change needs
reconciliation (see the GhostScheduler README's "Contract change proposal"
section and the M2_COORDINATION.md protocol). Until that lands, this module
is the enforced boundary: every raw, potentially-unbounded input is
clamped into [0,1] here, once, before any priority/stopping math ever sees
it -- nothing downstream in this package touches an un-normalized value.

Clamping (not raising) is the deliberate choice for out-of-range *input*,
because a producer emitting e.g. expected_evidence_gain=1.4 is not
malformed data (the field's current contract is only ``ge=0``, no upper
bound) -- it is exactly the "no normalization contract" gap this module
exists to close. Once inside a ``NormalizedPriorityFactorsV1``, the
invariant is absolute: a value here is in [0,1] or construction fails.
"""

from __future__ import annotations

import math
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ghostrange_contracts.enums import SecurityCriticality


def clamp01(value: float) -> float:
    """Clamp a real number into [0, 1]. Raises ValueError on NaN/inf, since
    those indicate an upstream computation bug, not a merely-unbounded
    value -- silently clamping a NaN to 0 or 1 would hide a real error.
    """
    if not math.isfinite(value):
        raise ValueError(f"cannot normalize non-finite value: {value!r}")
    return min(1.0, max(0.0, float(value)))


# Placeholder mapping from the categorical SecurityCriticality enum (the
# field TaskV1 actually has today) to a normalized [0,1] security_risk
# score. This is the scheduler-local stand-in for the "first-class
# security_risk: float field on TaskV1" that ADAPTIVE_COMPUTE.md's
# replacement formula wants; proposed additively in the GhostScheduler
# README/report rather than silently added to the frozen contract.
SECURITY_CRITICALITY_TO_RISK: dict[SecurityCriticality, float] = {
    SecurityCriticality.LOW: 0.25,
    SecurityCriticality.MEDIUM: 0.5,
    SecurityCriticality.HIGH: 0.75,
    SecurityCriticality.CRITICAL: 1.0,
}


def security_risk_from_criticality(criticality: SecurityCriticality) -> float:
    return SECURITY_CRITICALITY_TO_RISK[criticality]


# How many not-yet-terminal downstream dependents it takes to saturate
# dependency_criticality at 1.0. A task blocking 3+ pending tasks is
# "maximally dependency-critical" for v1 purposes; tunable, documented
# constant, not a magic number buried in a formula.
DEPENDENCY_CRITICALITY_SATURATION_COUNT = 3


def dependency_criticality_from_downstream_count(downstream_pending_count: int) -> float:
    if downstream_pending_count <= 0:
        return 0.0
    return clamp01(downstream_pending_count / DEPENDENCY_CRITICALITY_SATURATION_COUNT)


class NormalizedPriorityFactorsV1(BaseModel):
    """The four inputs to the ADAPTIVE_COMPUTE.md §4.3 priority formula,
    each guaranteed in [0, 1] by construction.

    - ``expected_evidence_gain``: normalized from ``TaskV1.expected_evidence_gain``
      (currently ``ge=0`` only, no upper bound at the contracts layer -- clamped here).
    - ``uncertainty``: from ``TaskV1.uncertainty`` (already contract-bound to [0,1];
      used as GhostScheduler v1's proxy for "uncertainty_reduction" -- see the
      README's "Known simplifications" section for why TaskV1 has no separate
      uncertainty_reduction field yet).
    - ``security_risk``: derived from ``TaskV1.security_criticality`` via
      ``security_risk_from_criticality``.
    - ``dependency_criticality``: derived from the World's dependency graph via
      ``dependency_criticality_from_downstream_count``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    SCHEMA_VERSION: ClassVar[str] = "1"

    expected_evidence_gain: float = Field(..., ge=0.0, le=1.0)
    uncertainty: float = Field(..., ge=0.0, le=1.0)
    security_risk: float = Field(..., ge=0.0, le=1.0)
    dependency_criticality: float = Field(..., ge=0.0, le=1.0)

    @field_validator(
        "expected_evidence_gain", "uncertainty", "security_risk", "dependency_criticality",
        mode="before",
    )
    @classmethod
    def _clamp_before_bounds_check(cls, v: float) -> float:
        """Clamp first so a caller passing a raw, unbounded upstream value
        (e.g. task.expected_evidence_gain=1.4) gets a well-defined
        normalized factor instead of a ValidationError -- the Field(ge=0,
        le=1) constraint below is then the *structural guarantee*, this
        validator is the *forgiving on-ramp* into that guarantee.
        """
        return clamp01(v)

    @classmethod
    def from_raw(
        cls,
        *,
        expected_evidence_gain: float,
        uncertainty: float,
        security_criticality: SecurityCriticality,
        downstream_pending_count: int,
    ) -> "NormalizedPriorityFactorsV1":
        """Convenience constructor from the raw fields GhostScheduler
        actually has available on ``TaskV1``/``WorldStateV1`` today.
        """
        return cls(
            expected_evidence_gain=expected_evidence_gain,
            uncertainty=uncertainty,
            security_risk=security_risk_from_criticality(security_criticality),
            dependency_criticality=dependency_criticality_from_downstream_count(
                downstream_pending_count
            ),
        )


__all__ = [
    "clamp01",
    "SECURITY_CRITICALITY_TO_RISK",
    "security_risk_from_criticality",
    "DEPENDENCY_CRITICALITY_SATURATION_COUNT",
    "dependency_criticality_from_downstream_count",
    "NormalizedPriorityFactorsV1",
]
