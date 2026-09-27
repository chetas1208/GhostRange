import math

import pytest

from ghostrange_scheduler.normalize import NormalizedPriorityFactorsV1
from ghostrange_scheduler.priority import (
    DEFAULT_COST_FLOOR_USD,
    DEFAULT_WEIGHTS,
    PriorityWeights,
    boost,
    compute_priority,
    value_score,
)


def _factors(**overrides) -> NormalizedPriorityFactorsV1:
    defaults = dict(
        expected_evidence_gain=0.5, uncertainty=0.5, security_risk=0.5, dependency_criticality=0.5
    )
    defaults.update(overrides)
    return NormalizedPriorityFactorsV1(**defaults)


def test_value_score_matches_weighted_log_sum_formula():
    factors = _factors(expected_evidence_gain=0.6, uncertainty=0.4)
    expected = 0.5 * math.log1p(0.6) + 0.5 * math.log1p(0.4)
    assert value_score(factors) == pytest.approx(expected)


def test_value_score_zero_evidence_gain_does_not_zero_the_whole_term():
    # This is the zero-collapse fix from ADAPTIVE_COMPUTE.md §4.1.2: one
    # factor at 0 should reduce, not annihilate, value_score.
    zeroed = _factors(expected_evidence_gain=0.0, uncertainty=0.8)
    nonzero = value_score(zeroed)
    assert nonzero > 0.0


def test_boost_floor_is_exactly_one_when_risk_and_dependency_are_zero():
    factors = _factors(security_risk=0.0, dependency_criticality=0.0)
    assert boost(factors) == 1.0


def test_boost_never_drops_below_one():
    factors = _factors(security_risk=1.0, dependency_criticality=1.0)
    assert boost(factors) == pytest.approx(1.0 + 0.5 + 0.5)


def test_boost_is_bounded_at_two_with_default_weights():
    factors = _factors(security_risk=1.0, dependency_criticality=1.0)
    assert boost(factors) <= 2.0 + 1e-9


def test_compute_priority_matches_manual_formula():
    factors = _factors(
        expected_evidence_gain=0.7, uncertainty=0.6, security_risk=0.8, dependency_criticality=0.2
    )
    cost = 1.0
    result = compute_priority(factors, cost)

    v = 0.5 * math.log1p(0.7) + 0.5 * math.log1p(0.6)
    b = 1.0 + 0.5 * 0.8 + 0.5 * 0.2
    raw = (v * b) / max(cost, DEFAULT_COST_FLOOR_USD)

    assert result.value_score == pytest.approx(v)
    assert result.boost == pytest.approx(b)
    assert result.priority_raw == pytest.approx(raw)
    assert result.expected_value == pytest.approx(v * b)
    assert result.priority_int == round(raw * 100)


def test_compute_priority_cost_floor_prevents_unbounded_blowup():
    factors = _factors(expected_evidence_gain=0.1, uncertainty=0.1)
    near_zero_cost_result = compute_priority(factors, 0.0000001)
    floor_cost_result = compute_priority(factors, DEFAULT_COST_FLOOR_USD)
    # Below the floor, cost is clamped to the floor -- results must be
    # identical, not scaled further by the tiny raw cost.
    assert near_zero_cost_result.priority_raw == pytest.approx(floor_cost_result.priority_raw)


def test_compute_priority_rejects_negative_cost():
    factors = _factors()
    with pytest.raises(ValueError):
        compute_priority(factors, -1.0)


def test_compute_priority_is_deterministic():
    factors = _factors(expected_evidence_gain=0.42, uncertainty=0.33)
    a = compute_priority(factors, 0.75)
    b = compute_priority(factors, 0.75)
    assert a == b


def test_higher_evidence_gain_yields_higher_priority_all_else_equal():
    low = compute_priority(_factors(expected_evidence_gain=0.1), 1.0)
    high = compute_priority(_factors(expected_evidence_gain=0.9), 1.0)
    assert high.priority_raw > low.priority_raw


def test_custom_weights_are_respected():
    factors = _factors(expected_evidence_gain=0.5, uncertainty=0.5)
    weights = PriorityWeights(w1_evidence_gain=1.0, w2_uncertainty=0.0)
    result = compute_priority(factors, 1.0, weights=weights)
    assert result.value_score == pytest.approx(math.log1p(0.5))
