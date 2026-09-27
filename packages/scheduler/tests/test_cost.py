import uuid

import pytest

from ghostrange_contracts.cluster_state import ClusterStateV1
from ghostrange_contracts.enums import ResourceClass
from ghostrange_scheduler.cost import (
    DEFAULT_RATE_CARD_USD_PER_HOUR,
    estimate_cost_usd,
    hourly_rate_usd,
)


def test_hourly_rate_falls_back_to_default_rate_card_when_no_cluster_state():
    assert hourly_rate_usd(ResourceClass.CPU_SMALL, None) == DEFAULT_RATE_CARD_USD_PER_HOUR[ResourceClass.CPU_SMALL]


def test_hourly_rate_falls_back_when_cluster_state_has_no_entry_for_class():
    cluster = ClusterStateV1(range_id=uuid.uuid4())
    assert hourly_rate_usd(ResourceClass.GPU_LARGE, cluster) == DEFAULT_RATE_CARD_USD_PER_HOUR[ResourceClass.GPU_LARGE]


def test_hourly_rate_prefers_cluster_state_observed_rate():
    cluster = ClusterStateV1(
        range_id=uuid.uuid4(), rate_card_usd_per_hour={ResourceClass.CPU_SMALL: 0.0099}
    )
    assert hourly_rate_usd(ResourceClass.CPU_SMALL, cluster) == 0.0099


def test_estimate_cost_usd_uses_minimum_billing_quantum():
    seven_min = estimate_cost_usd(ResourceClass.CPU_SMALL, 420)
    one_hour = estimate_cost_usd(ResourceClass.CPU_SMALL, 3600)
    two_hours = estimate_cost_usd(ResourceClass.CPU_SMALL, 7200)
    assert seven_min == pytest.approx(one_hour)
    assert two_hours == pytest.approx(2 * one_hour)


def test_estimate_cost_usd_zero_duration_is_free():
    assert estimate_cost_usd(ResourceClass.GPU_LARGE, 0) == 0.0


def test_estimate_cost_usd_rejects_negative_duration():
    with pytest.raises(ValueError):
        estimate_cost_usd(ResourceClass.CPU_SMALL, -1)


def test_gpu_large_matches_documented_h100_per_gpu_rate():
    # Real figure from docs/research/VULTR.md §2: $23.92/hr chassis / 8 GPUs.
    assert DEFAULT_RATE_CARD_USD_PER_HOUR[ResourceClass.GPU_LARGE] == pytest.approx(2.99)


def test_every_resource_class_has_a_rate_card_entry():
    for resource_class in ResourceClass:
        assert resource_class in DEFAULT_RATE_CARD_USD_PER_HOUR
