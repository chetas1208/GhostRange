"""Property-style invariants for cost ledger."""

import uuid

from ghostrange_contracts.cost_v1 import CostReservationV1, ResourceCostRecordV1, ResourceLifecycleTimestampsV1
from ghostrange_cost.ledger import GhostCostLedger
from ghostrange_cost.money import usd_to_micros


def test_cost_non_negative():
    ledger = GhostCostLedger()
    rid = "r1"
    ledger.register_resource(
        ResourceCostRecordV1(
            resource_id=rid,
            product="cloud_compute",
            price_snapshot_id=uuid.uuid4(),
        ),
        hourly_rate_usd_micros=usd_to_micros("0.1"),
    )
    ledger.refresh_resource_accrual(rid, provider_lifetime_seconds=3600)
    snap = ledger.campaign_snapshot("c1")
    assert snap.total_known_usd_micros >= 0


def test_duplicate_inference_idempotent():
    from ghostrange_contracts.cost_v1 import InferenceUsageRecordV1

    ledger = GhostCostLedger()
    u = InferenceUsageRecordV1(
        request_id="req-1",
        model="m",
        input_tokens=100,
        output_tokens=50,
        calculated_usd_micros=1000,
    )
    ledger.record_inference(u)
    ledger.record_inference(u)
    snap = ledger.campaign_snapshot("c1")
    assert snap.categories.get("INFERENCE", 0) == 1000
