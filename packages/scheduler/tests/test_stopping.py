import uuid

import pytest

from ghostrange_contracts.cluster_state import BudgetStateV1
from ghostrange_contracts.policy import BudgetV1
from ghostrange_scheduler.stopping import (
    DEFAULT_BASE_FLOOR_THRESHOLD,
    DEFAULT_C_MIN_USD,
    effective_stop,
    floor_threshold,
    marginal_voi_ratio,
    should_stop,
)


def test_marginal_voi_ratio_matches_formula():
    ratio = marginal_voi_ratio(g_hat=0.8, c_hat=2.0, risk=0.5, dep=0.5)
    assert ratio == pytest.approx((0.8 * 0.5 * 0.5) / 2.0)


def test_marginal_voi_ratio_applies_cost_floor_near_zero_cost():
    ratio_tiny_cost = marginal_voi_ratio(g_hat=1.0, c_hat=1e-9, risk=1.0, dep=1.0, c_min=0.01)
    ratio_at_floor = marginal_voi_ratio(g_hat=1.0, c_hat=0.01, risk=1.0, dep=1.0, c_min=0.01)
    assert ratio_tiny_cost == pytest.approx(ratio_at_floor)


def test_marginal_voi_ratio_rejects_negative_inputs():
    with pytest.raises(ValueError):
        marginal_voi_ratio(g_hat=-1.0, c_hat=1.0, risk=1.0, dep=1.0)


def test_marginal_voi_ratio_zero_dependency_does_not_zero_collapse_the_ratio():
    # The literal §3.1 formula is a strict product: dep=0 (the common
    # case -- a leaf task with no downstream dependents) would otherwise
    # zero out the entire ratio regardless of how valuable g_hat is. Our
    # documented mitigation floors risk/dep at ZERO_FACTOR_FLOOR so an
    # absent (not measured-and-zero) signal doesn't swamp a real g_hat.
    ratio = marginal_voi_ratio(g_hat=0.6, c_hat=0.02, risk=0.25, dep=0.0)
    assert ratio > 0.0


def test_marginal_voi_ratio_zero_dependency_floor_is_exact():
    ratio = marginal_voi_ratio(g_hat=0.6, c_hat=0.02, risk=0.25, dep=0.0, zero_factor_floor=0.1)
    assert ratio == pytest.approx((0.6 * 0.25 * 0.1) / 0.02)


def test_marginal_voi_ratio_genuinely_zero_gain_still_drives_ratio_to_zero():
    # g_hat/c_hat are NOT floored -- a real zero remaining evidence gain
    # should still produce a zero ratio; only risk/dep get the epsilon.
    ratio = marginal_voi_ratio(g_hat=0.0, c_hat=1.0, risk=1.0, dep=1.0)
    assert ratio == 0.0


def test_floor_threshold_without_budget_is_base_floor():
    assert floor_threshold(None) == DEFAULT_BASE_FLOOR_THRESHOLD


def test_floor_threshold_rises_as_headroom_shrinks():
    full_budget = BudgetV1(range_id=uuid.uuid4(), max_total_cost_usd=100, spent_cost_usd=0, max_duration_seconds=3600)
    scarce_budget = BudgetV1(range_id=uuid.uuid4(), max_total_cost_usd=100, spent_cost_usd=95, max_duration_seconds=3600)

    full_floor = floor_threshold(BudgetStateV1(budget=full_budget))
    scarce_floor = floor_threshold(BudgetStateV1(budget=scarce_budget))

    assert scarce_floor > full_floor
    assert full_floor == pytest.approx(DEFAULT_BASE_FLOOR_THRESHOLD)


def test_floor_threshold_at_full_exhaustion_is_base_times_one_plus_sensitivity():
    exhausted_budget = BudgetV1(
        range_id=uuid.uuid4(), max_total_cost_usd=100, spent_cost_usd=100, max_duration_seconds=3600
    )
    result = floor_threshold(BudgetStateV1(budget=exhausted_budget))
    assert result == pytest.approx(DEFAULT_BASE_FLOOR_THRESHOLD * (1.0 + 4.0))


def test_should_stop_fires_when_ratio_below_floor():
    result = should_stop(g_hat=0.01, c_hat=5.0, risk=0.5, dep=0.5)
    assert result.stop is True
    assert result.dominant_factor == "gain"


def test_should_stop_does_not_fire_when_ratio_clears_floor():
    result = should_stop(g_hat=1.0, c_hat=0.01, risk=1.0, dep=1.0, c_min=DEFAULT_C_MIN_USD)
    assert result.stop is False
    assert result.dominant_factor == "cost"


def test_should_stop_is_deterministic():
    a = should_stop(g_hat=0.3, c_hat=1.2, risk=0.4, dep=0.6)
    b = should_stop(g_hat=0.3, c_hat=1.2, risk=0.4, dep=0.6)
    assert a == b


def test_effective_stop_budget_exhausted_forces_stop_regardless_of_dependency():
    should_stop_result, reason = effective_stop(
        stop_recommended=False,
        dependency_criticality=1.0,
        downstream_blocked_without=True,
        budget_exhausted=True,
    )
    assert should_stop_result is True
    assert reason == "stop"


def test_effective_stop_dependency_veto_overrides_stop_recommendation():
    should_stop_result, reason = effective_stop(
        stop_recommended=True,
        dependency_criticality=0.9,
        downstream_blocked_without=True,
        budget_exhausted=False,
    )
    assert should_stop_result is False
    assert reason == "dependency_veto"


def test_effective_stop_low_dependency_criticality_does_not_veto():
    should_stop_result, reason = effective_stop(
        stop_recommended=True,
        dependency_criticality=0.1,
        downstream_blocked_without=True,
        budget_exhausted=False,
    )
    assert should_stop_result is True
    assert reason == "stop"


def test_effective_stop_no_stop_recommended_is_continue():
    should_stop_result, reason = effective_stop(
        stop_recommended=False,
        dependency_criticality=0.0,
        downstream_blocked_without=False,
        budget_exhausted=False,
    )
    assert should_stop_result is False
    assert reason == "continue"


def test_effective_stop_precedence_budget_beats_dependency_veto_explicitly():
    # The doc's explicit warning: "this precedence should be encoded
    # explicitly in code... because silent implicit ordering is exactly
    # the kind of thing that breaks explainability later." Assert budget
    # wins even when every dependency-veto condition is also satisfied.
    should_stop_result, reason = effective_stop(
        stop_recommended=True,
        dependency_criticality=1.0,
        downstream_blocked_without=True,
        budget_exhausted=True,
    )
    assert should_stop_result is True
    assert reason == "stop"
