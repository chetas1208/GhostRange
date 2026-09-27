"""The GhostScheduler v1 priority formula: ADAPTIVE_COMPUTE.md §4.3's
proposed replacement for the naive multiplicative candidate formula,
implemented exactly as specified there:

    value_score = w1 * log(1 + expected_evidence_gain) + w2 * log(1 + uncertainty)
    boost       = 1 + w3 * security_risk + w4 * dependency_criticality
    priority    = (value_score * boost) / max(estimated_cost_usd, cost_floor)

See the package README for the full "why this formula" writeup (units
mismatch / zero-collapse / unbounded-denominator critique of the naive
candidate, and how each term here addresses it). This module only holds
the callable math; ``scheduler.py`` wires it into `schedule()` and adds the
reason-code explanations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .normalize import NormalizedPriorityFactorsV1

# Default weights. All four start equal (0.5) per ADAPTIVE_COMPUTE.md's
# worked example ("w3, w4 tunable, e.g. start at 0.5 each, so max boost is a
# 2x multiplier, not unbounded") -- w1/w2 follow the same convention for
# consistency, giving equal initial weight to evidence-gain and
# uncertainty inside value_score.
DEFAULT_W1_EVIDENCE_GAIN = 0.5
DEFAULT_W2_UNCERTAINTY = 0.5
DEFAULT_W3_SECURITY_RISK = 0.5
DEFAULT_W4_DEPENDENCY_CRITICALITY = 0.5

# Cost floor: prevents the unbounded-blowup failure mode ADAPTIVE_COMPUTE.md
# §4.1.3 calls out ("priority is unbounded as cost approaches zero"). A
# task cheaper than one cent effectively costs one cent for ranking
# purposes. Distinct from (but same idea as) stopping.py's c_min -- this
# one bounds the *priority score*, that one bounds the *stopping ratio*;
# kept as separate named constants since they are conceptually different
# knobs even though they currently share a value.
DEFAULT_COST_FLOOR_USD = 0.01

# priority (float, unbounded-but-typically-small) is scaled into
# SchedulerDecisionV1.priority (an int) by this factor. 100 gives ~2
# decimal digits of resolution before truncation, which is enough
# granularity to break ties between tasks whose priority_raw differs in
# the second decimal place without needing float priority on the wire
# contract.
PRIORITY_INT_SCALE = 100
PRIORITY_INT_MAX = 1_000_000


@dataclass(frozen=True)
class PriorityWeights:
    w1_evidence_gain: float = DEFAULT_W1_EVIDENCE_GAIN
    w2_uncertainty: float = DEFAULT_W2_UNCERTAINTY
    w3_security_risk: float = DEFAULT_W3_SECURITY_RISK
    w4_dependency_criticality: float = DEFAULT_W4_DEPENDENCY_CRITICALITY


DEFAULT_WEIGHTS = PriorityWeights()


@dataclass(frozen=True)
class PriorityResult:
    """Every term kept separate and inspectable, per ADAPTIVE_COMPUTE.md's
    explicit requirement that the formula's terms map cleanly to reason
    codes ("value_score maps cleanly to HIGH_UNCERTAINTY/
    CHEAP_INFORMATION_GAIN-type codes, boost maps cleanly to
    HIGH_ASSET_RISK/DEPENDENCY_CRITICAL-type codes").
    """

    value_score: float
    boost: float
    priority_raw: float
    expected_value: float  # value_score * boost -- the unitless score SchedulerDecisionV1.expected_value wants
    priority_int: int


def value_score(factors: NormalizedPriorityFactorsV1, weights: PriorityWeights = DEFAULT_WEIGHTS) -> float:
    return weights.w1_evidence_gain * math.log1p(factors.expected_evidence_gain) + (
        weights.w2_uncertainty * math.log1p(factors.uncertainty)
    )


def boost(factors: NormalizedPriorityFactorsV1, weights: PriorityWeights = DEFAULT_WEIGHTS) -> float:
    """Bounded additive boost, floor 1 (neutral -- "no risk/dependency
    contribution at all still leaves boost = 1, i.e. neutral, not a
    penalty", ADAPTIVE_COMPUTE.md §4.3). Floor 1 holds automatically here
    because security_risk/dependency_criticality are both in [0,1] and
    weights are non-negative, but is asserted explicitly rather than left
    implicit, since a future negative-weight experiment could otherwise
    silently break the documented invariant.
    """
    value = 1.0 + weights.w3_security_risk * factors.security_risk + (
        weights.w4_dependency_criticality * factors.dependency_criticality
    )
    assert value >= 1.0, "boost must never drop below its documented floor of 1.0"
    return value


def compute_priority(
    factors: NormalizedPriorityFactorsV1,
    estimated_cost_usd: float,
    *,
    weights: PriorityWeights = DEFAULT_WEIGHTS,
    cost_floor_usd: float = DEFAULT_COST_FLOOR_USD,
) -> PriorityResult:
    if estimated_cost_usd < 0:
        raise ValueError("estimated_cost_usd must be >= 0")

    v_score = value_score(factors, weights)
    b = boost(factors, weights)
    effective_cost = max(estimated_cost_usd, cost_floor_usd)
    raw = (v_score * b) / effective_cost
    priority_int = min(PRIORITY_INT_MAX, max(0, round(raw * PRIORITY_INT_SCALE)))

    return PriorityResult(
        value_score=v_score,
        boost=b,
        priority_raw=raw,
        expected_value=v_score * b,
        priority_int=priority_int,
    )


__all__ = [
    "DEFAULT_W1_EVIDENCE_GAIN",
    "DEFAULT_W2_UNCERTAINTY",
    "DEFAULT_W3_SECURITY_RISK",
    "DEFAULT_W4_DEPENDENCY_CRITICALITY",
    "DEFAULT_COST_FLOOR_USD",
    "PRIORITY_INT_SCALE",
    "PRIORITY_INT_MAX",
    "PriorityWeights",
    "DEFAULT_WEIGHTS",
    "PriorityResult",
    "value_score",
    "boost",
    "compute_priority",
]
