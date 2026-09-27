import math

import pytest
from pydantic import ValidationError

from ghostrange_contracts.enums import SecurityCriticality
from ghostrange_scheduler.normalize import (
    NormalizedPriorityFactorsV1,
    clamp01,
    dependency_criticality_from_downstream_count,
    security_risk_from_criticality,
)


def test_clamp01_passes_through_in_range_values():
    assert clamp01(0.0) == 0.0
    assert clamp01(1.0) == 1.0
    assert clamp01(0.42) == 0.42


def test_clamp01_clamps_out_of_range_values():
    assert clamp01(-5.0) == 0.0
    assert clamp01(1.4) == 1.0


def test_clamp01_rejects_non_finite():
    with pytest.raises(ValueError):
        clamp01(math.inf)
    with pytest.raises(ValueError):
        clamp01(math.nan)


@pytest.mark.parametrize(
    "criticality,expected",
    [
        (SecurityCriticality.LOW, 0.25),
        (SecurityCriticality.MEDIUM, 0.5),
        (SecurityCriticality.HIGH, 0.75),
        (SecurityCriticality.CRITICAL, 1.0),
    ],
)
def test_security_risk_from_criticality(criticality, expected):
    assert security_risk_from_criticality(criticality) == expected


def test_dependency_criticality_zero_when_no_pending():
    assert dependency_criticality_from_downstream_count(0) == 0.0


def test_dependency_criticality_saturates_at_one():
    assert dependency_criticality_from_downstream_count(3) == 1.0
    assert dependency_criticality_from_downstream_count(100) == 1.0


def test_dependency_criticality_scales_below_saturation():
    result = dependency_criticality_from_downstream_count(1)
    assert 0.0 < result < 1.0
    assert result == pytest.approx(1 / 3)


def test_normalized_factors_clamps_out_of_range_expected_evidence_gain():
    # TaskV1.expected_evidence_gain is only ge=0, no upper bound today --
    # this is the exact gap this model exists to close.
    factors = NormalizedPriorityFactorsV1(
        expected_evidence_gain=5.0,
        uncertainty=0.5,
        security_risk=0.5,
        dependency_criticality=0.5,
    )
    assert factors.expected_evidence_gain == 1.0


def test_normalized_factors_rejects_negative_after_clamp_is_still_in_bounds():
    factors = NormalizedPriorityFactorsV1(
        expected_evidence_gain=-3.0,
        uncertainty=0.5,
        security_risk=0.5,
        dependency_criticality=0.5,
    )
    assert factors.expected_evidence_gain == 0.0


def test_normalized_factors_from_raw():
    factors = NormalizedPriorityFactorsV1.from_raw(
        expected_evidence_gain=0.8,
        uncertainty=0.3,
        security_criticality=SecurityCriticality.HIGH,
        downstream_pending_count=2,
    )
    assert factors.expected_evidence_gain == 0.8
    assert factors.uncertainty == 0.3
    assert factors.security_risk == 0.75
    assert factors.dependency_criticality == pytest.approx(2 / 3)


def test_normalized_factors_is_frozen():
    factors = NormalizedPriorityFactorsV1(
        expected_evidence_gain=0.1, uncertainty=0.1, security_risk=0.1, dependency_criticality=0.1
    )
    with pytest.raises(ValidationError):
        factors.expected_evidence_gain = 0.9


def test_normalized_factors_forbids_extra_fields():
    with pytest.raises(ValidationError):
        NormalizedPriorityFactorsV1(
            expected_evidence_gain=0.1,
            uncertainty=0.1,
            security_risk=0.1,
            dependency_criticality=0.1,
            extra_field="not allowed",
        )
