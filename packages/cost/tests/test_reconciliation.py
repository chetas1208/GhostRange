from ghostrange_cost.reconciliation import ReconciliationStatus, reconcile_campaign_cost


def test_provider_unavailable_is_honest():
    rec = reconcile_campaign_cost(campaign_id="c1", calculated_usd_micros=100_000, provider_reported_usd_micros=None)
    assert rec.status == ReconciliationStatus.PROVIDER_UNAVAILABLE
    assert rec.calculated_usd_micros == 100_000


def test_matched_within_tolerance():
    rec = reconcile_campaign_cost(
        campaign_id="c1",
        calculated_usd_micros=1_000_000,
        provider_reported_usd_micros=1_005_000,
        tolerance_micros=10_000,
    )
    assert rec.status == ReconciliationStatus.MATCHED


def test_difference_outside_tolerance():
    rec = reconcile_campaign_cost(
        campaign_id="c1",
        calculated_usd_micros=1_000_000,
        provider_reported_usd_micros=1_500_000,
    )
    assert rec.status == ReconciliationStatus.DIFFERENCE
