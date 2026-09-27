"""Termination/stopping awareness: ADAPTIVE_COMPUTE.md §3.1's Function A --
"Marginal Value-of-Information Ratio with Floor" -- the doc's own
recommended default for v0/v1 ("Why this is the recommended default: it
directly operationalizes the VoI framing... with the fewest moving parts,
requires no probability distributions or posteriors... and every term is
independently inspectable for the reason-code output.").

    marginal_ratio(t) = (g_hat(t) * risk(t) * dep(t)) / max(c_hat(t), c_min)
    STOP if marginal_ratio(t) < floor_threshold

Deliberately implemented exactly as specified in the doc, INCLUDING its
multiplicative g_hat*risk*dep numerator -- this is a different formula
from the priority formula in ``priority.py`` (which replaces multiplication
with a log-sum specifically to fix zero-collapse for *that* formula's use
case, per ADAPTIVE_COMPUTE.md §4). The doc keeps Function A's own shape
multiplicative by design: it is a ratio against a floor, not a ranking
score, and the doc's §3.1 does not carry the §4 critique over to it. Do
not "fix" this into a log-sum without re-reading §3 vs §4 -- they are
answering different questions (continue-vs-stop, not who-runs-first) and
were deliberately kept structurally distinct in the source research.

Only Function A is implemented for real per the task brief ("implement
ONE of the three... recommend Option A"). Function B (slope detector) and
the estimator-interface forward-compat note (§3.4) are intentionally not
implemented in v1 -- see the README's "Not implemented" section.

Function C (§3.3, the dependency/budget veto layer) IS implemented below
as ``effective_stop``, because it is pure, cheap, deterministic boolean
logic needed to get the *precedence* right (BUDGET_EXHAUSTED overrides
DEPENDENCY_CRITICAL, never the reverse) -- getting this backwards is
exactly the "easy to implement backwards" trap the doc warns about, so it
is centralized in one tested function rather than left to ad hoc
if/else ordering in scheduler.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from ghostrange_contracts.cluster_state import BudgetStateV1

# Small floor cost, c_min in the doc's notation: avoids a "division
# blow-up when remaining estimated cost is near zero" (§3.1). Same value
# and same rationale as priority.py's DEFAULT_COST_FLOOR_USD, kept as an
# independent named constant since the two ratios (priority vs. stopping)
# are conceptually different knobs that happen to start at the same value.
DEFAULT_C_MIN_USD = 0.01

# Base floor_threshold: the "minimum acceptable evidence-per-dollar"
# baseline the doc asks for ("floor_threshold is a single tunable knob,
# ideally expressed as 'minimum acceptable evidence-per-dollar'"), before
# any budget-conditioning is applied. Chosen so that a task with
# g_hat=risk=dep=1.0 and c_hat=$1 (ratio=1.0) clears an unconstrained
# floor of 0.05 comfortably, while a task producing near-zero evidence
# gain for the same cost does not -- a deliberately loose default in the
# absence of empirical calibration data (v1, one range, modest services).
DEFAULT_BASE_FLOOR_THRESHOLD = 0.05

# --- OUR DESIGN DECISION (Agent 10), a small flagged deviation from the
# literal §3.1 pseudocode, not the log-sum redesign §4 explicitly warns
# against re-applying here:
#
# dependency_criticality is legitimately 0 for the common case of a leaf
# task with no downstream dependents (most tasks have none -- dependency
# graphs are mostly shallow). Because marginal_voi_ratio is a strict
# three-way product (g_hat * risk * dep), a literal dep=0 collapses the
# *entire* ratio to 0 regardless of g_hat -- meaning Function A as
# literally specified would recommend stopping almost every ordinary leaf
# task, independent of how much remaining evidence it's expected to
# produce. That is the exact zero-collapse failure mode ADAPTIVE_COMPUTE.md
# §4.1.2 identifies for the *priority* formula's multiplicative shape --
# the doc just doesn't carry that critique over to Function A's identical
# shape, which looks like an oversight rather than an intentional choice
# (§3.1's own text never discusses risk(t)/dep(t)==0 as a case). Treating
# "no measured dependency signal" as a hard zero multiplier conflates
# "definitely not needed" with "not yet measured", which is precisely the
# distinction §4.1.2 warns against collapsing.
#
# Mitigation (deliberately narrow, not a formula-shape change): floor
# risk/dep at a small epsilon before multiplying, so an unmeasured/absent
# factor acts as "weak signal", not "zero out everything". The formula's
# shape (product-over-cost-with-floor) is unchanged; only literal-zero
# inputs are treated as epsilon instead. See packages/scheduler/README.md
# "Known deviations from the research doc" for the worked-example numbers
# that motivated this (a straggling-but-still-valuable task was
# incorrectly recommended for termination without it).
ZERO_FACTOR_FLOOR = 0.1

# How strongly floor_threshold rises as budget headroom shrinks. At
# headroom_fraction=1.0 (full budget remaining) the multiplier is 1x (no
# change); at headroom_fraction=0.0 (exhausted) the multiplier is
# (1 + BUDGET_FLOOR_SENSITIVITY)x. Per the doc: "as budget gets scarcer,
# floor_threshold should rise, making the scheduler pickier automatically."
BUDGET_FLOOR_SENSITIVITY = 4.0


def floor_threshold(
    budget_state: Optional[BudgetStateV1],
    *,
    base_floor: float = DEFAULT_BASE_FLOOR_THRESHOLD,
    sensitivity: float = BUDGET_FLOOR_SENSITIVITY,
) -> float:
    """Budget-conditioned floor_threshold, per ADAPTIVE_COMPUTE.md §3.1's
    footnote: "a concrete, deterministic link between budget state and
    stopping behavior, which the naive multiplicative priority formula
    has no mechanism for at all."

    No budget configured -> the unconditioned base floor (a scheduler
    running without a budget policy attached has no headroom signal to
    condition on, so it can't be pickier "because money is scarce" --
    that's a different, budget-config-owner problem, not something this
    function should assume).
    """
    if budget_state is None:
        return base_floor
    headroom = budget_state.headroom_fraction  # in [0, 1], 1.0 = full budget left
    scarcity = 1.0 - headroom
    return base_floor * (1.0 + sensitivity * scarcity)


@dataclass(frozen=True)
class MarginalRatioResult:
    ratio: float
    threshold: float
    stop: bool
    dominant_factor: Literal["gain", "cost", "n/a"]


def marginal_voi_ratio(
    g_hat: float,
    c_hat: float,
    risk: float,
    dep: float,
    *,
    c_min: float = DEFAULT_C_MIN_USD,
    zero_factor_floor: float = ZERO_FACTOR_FLOOR,
) -> float:
    """The raw ratio, exposed standalone so callers (and tests) can reason
    about it independently of the stop/continue threshold comparison.

    ``risk``/``dep`` are floored at ``zero_factor_floor`` before
    multiplying -- see the ``ZERO_FACTOR_FLOOR`` module docstring above
    for why. ``g_hat``/``c_hat`` are NOT floored the same way: a
    genuinely-zero remaining evidence gain really should drive the ratio
    to (near) zero, that is the formula working as intended, not a gap.
    """
    for name, value in (("g_hat", g_hat), ("c_hat", c_hat), ("risk", risk), ("dep", dep)):
        if value < 0:
            raise ValueError(f"{name} must be >= 0, got {value!r}")
    effective_risk = max(risk, zero_factor_floor)
    effective_dep = max(dep, zero_factor_floor)
    return (g_hat * effective_risk * effective_dep) / max(c_hat, c_min)


def should_stop(
    g_hat: float,
    c_hat: float,
    risk: float,
    dep: float,
    *,
    budget_state: Optional[BudgetStateV1] = None,
    c_min: float = DEFAULT_C_MIN_USD,
    base_floor: float = DEFAULT_BASE_FLOOR_THRESHOLD,
    zero_factor_floor: float = ZERO_FACTOR_FLOOR,
) -> MarginalRatioResult:
    """Function A applied end to end: compute the ratio, compute the
    (possibly budget-conditioned) floor, and compare.

    ``dominant_factor`` is a lightweight explainability aid distinguishing
    the doc's two named cases: "fires MARGINAL_GAIN_LOW when g_hat(t) is
    the dominant reason the ratio is low; fires CHEAP_INFORMATION_GAIN as
    the inverse signal... when the ratio is high because c_hat(t) is
    unusually low, not because g_hat is high." It is a simple heuristic
    (compare each term's distance from a "typical" reference value of 1.0,
    ratio dominance goes to whichever term is more extreme), not a formal
    sensitivity/gradient decomposition -- sufficient for a reason-code
    hint, not a scientific attribution.
    """
    threshold = floor_threshold(budget_state, base_floor=base_floor)
    ratio = marginal_voi_ratio(g_hat, c_hat, risk, dep, c_min=c_min, zero_factor_floor=zero_factor_floor)
    stop = ratio < threshold

    if g_hat <= c_min and c_hat <= c_min:
        dominant: Literal["gain", "cost", "n/a"] = "n/a"
    elif g_hat < c_hat:
        dominant = "gain"
    else:
        dominant = "cost"

    return MarginalRatioResult(ratio=ratio, threshold=threshold, stop=stop, dominant_factor=dominant)


def effective_stop(
    *,
    stop_recommended: bool,
    dependency_criticality: float,
    downstream_blocked_without: bool,
    budget_exhausted: bool,
    dependency_critical_threshold: float = 0.66,
) -> tuple[bool, Literal["stop", "dependency_veto", "continue"]]:
    """ADAPTIVE_COMPUTE.md §3.3, Function C, implemented as the explicit
    ordered precedence the doc insists on:

        effective_stop = (stop_recommended)
                          AND NOT (dep >= dependency_critical_threshold
                                    AND downstream_blocked_without)
                          AND NOT budget_exhausted_override
        budget_exhausted_override FORCES stop regardless of dependency veto.

    Returns ``(should_actually_stop, veto_reason)`` where ``veto_reason``
    is one of:
    - "stop": stopping recommendation stands (or budget forces it).
    - "dependency_veto": would have stopped, but a dependency override
      kept it alive (maps to DEPENDENCY_CRITICAL).
    - "continue": no stop was recommended in the first place.
    """
    if budget_exhausted:
        return True, "stop"

    if not stop_recommended:
        return False, "continue"

    dependency_veto = (
        dependency_criticality >= dependency_critical_threshold and downstream_blocked_without
    )
    if dependency_veto:
        return False, "dependency_veto"

    return True, "stop"


__all__ = [
    "DEFAULT_C_MIN_USD",
    "DEFAULT_BASE_FLOOR_THRESHOLD",
    "ZERO_FACTOR_FLOOR",
    "BUDGET_FLOOR_SENSITIVITY",
    "floor_threshold",
    "MarginalRatioResult",
    "marginal_voi_ratio",
    "should_stop",
    "effective_stop",
]
