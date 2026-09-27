import uuid

from ghostrange_contracts.cost_v1 import ResourceCostRecordV1, ResourceLifecycleTimestampsV1
from ghostrange_cost.ledger import GhostCostLedger


def test_export_import_roundtrip_preserves_snapshot_total():
    ledger = GhostCostLedger()
    ps = uuid.uuid4()
    rec = ResourceCostRecordV1(
        resource_id="w1",
        campaign_id="camp-1",
        product="cloud_compute",
        price_snapshot_id=ps,
        lifecycle=ResourceLifecycleTimestampsV1(),
        accrued_estimate_usd_micros=24000,
        committed_usd_micros=24000,
    )
    ledger.register_resource(rec, hourly_rate_usd_micros=24000, event_id="e1")
    state = ledger.export_state()
    ledger2 = GhostCostLedger()
    ledger2.import_state(state)
    a = ledger.campaign_snapshot("camp-1").total_known_usd_micros
    b = ledger2.campaign_snapshot("camp-1").total_known_usd_micros
    assert a == b == 24000
