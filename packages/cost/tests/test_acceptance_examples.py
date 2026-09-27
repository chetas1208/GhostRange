"""Acceptance examples A–G from cost accounting spec."""

import uuid

import pytest

from ghostrange_cost.attribution import attribute_wall_time_share, campaign_total_from_resources
from ghostrange_cost.compute_billing import compute_ephemeral_cost_usd_micros
from ghostrange_cost.inference_billing import inference_cost_usd_micros
from ghostrange_cost.ledger import GhostCostLedger
from ghostrange_cost.money import micros_to_usd_decimal, usd_to_micros
from ghostrange_contracts.cost_v1 import CostReservationV1, ResourceCostRecordV1, ResourceLifecycleTimestampsV1

import importlib.util
from pathlib import Path

_ref_path = Path(__file__).resolve().parent / "reference_calculator.py"
_ref_spec = importlib.util.spec_from_file_location("ghostrange_cost_ref_calc", _ref_path)
assert _ref_spec and _ref_spec.loader
_ref_mod = importlib.util.module_from_spec(_ref_spec)
_ref_spec.loader.exec_module(_ref_mod)
ref_compute_cost_usd = _ref_mod.ref_compute_cost_usd
ref_inference_usd = _ref_mod.ref_inference_usd


# Example A — 7 minute VM, $P/hr, one-hour minimum
@pytest.mark.parametrize("p", ["0.10", "0.024"])
def test_example_a_short_lived_vm(p: str):
    lifetime = 7 * 60
    ref = ref_compute_cost_usd(float(p), lifetime)
    got = compute_ephemeral_cost_usd_micros(hourly_rate_usd=p, provider_lifetime_seconds=lifetime)
    assert float(micros_to_usd_decimal(got.total_usd_micros)) == pytest.approx(ref)
    assert got.billable_hours == 1
    wrong_per_second = float(p) * (lifetime / 3600)
    assert float(micros_to_usd_decimal(got.total_usd_micros)) > wrong_per_second


def test_example_b_worker_reuse_single_resource():
    p = 0.10
    resource_micros = compute_ephemeral_cost_usd_micros(
        hourly_rate_usd=str(p), provider_lifetime_seconds=20 * 60
    ).total_usd_micros
    attrs = attribute_wall_time_share(
        resource_total_usd_micros=resource_micros,
        task_durations_seconds={"A": 7 * 60, "B": 8 * 60},
    )
    assert sum(attrs.values()) == resource_micros
    campaign = campaign_total_from_resources([resource_micros])
    assert campaign == resource_micros
    assert campaign != resource_micros * 2


def test_example_c_speculation_two_workers():
    p = 0.10
    w1 = compute_ephemeral_cost_usd_micros(hourly_rate_usd=str(p), provider_lifetime_seconds=600).total_usd_micros
    w2 = compute_ephemeral_cost_usd_micros(hourly_rate_usd=str(p), provider_lifetime_seconds=600).total_usd_micros
    total = campaign_total_from_resources([w1, w2])
    assert total == w1 + w2


def test_example_d_inference_tokens():
    ref = ref_inference_usd(1_000_000, 500_000, 0.55, 2.75)
    got = inference_cost_usd_micros(
        model="mixtral-8x7b",
        input_tokens=1_000_000,
        output_tokens=500_000,
        input_price_per_million_usd="0.55",
        output_price_per_million_usd="2.75",
    )
    assert got is not None
    assert float(micros_to_usd_decimal(got.total_usd_micros)) == pytest.approx(ref, rel=1e-6)


def test_example_e_teardown_timeout_continues_accrual():
    from ghostrange_cost.compute_billing import accrue_running_resource_usd_micros

    rate = usd_to_micros("0.10")
    accrued, state = accrue_running_resource_usd_micros(
        hourly_rate_usd_micros=rate,
        provider_lifetime_seconds=3600,
        destroy_requested=True,
        provider_destroyed=False,
    )
    assert state == "BILLING_END_UNCONFIRMED"
    assert accrued == rate


def test_example_f_concurrent_budget_reservation():
    ledger = GhostCostLedger()
    ledger.configure_budget_cap_usd_micros(usd_to_micros("0.10"))
    cid = "camp-1"
    ok1 = ledger.reserve(
        CostReservationV1(
            reservation_id=uuid.uuid4(),
            campaign_id=cid,
            reserved_usd_micros=usd_to_micros("0.08"),
            reason="provision",
        )
    )
    ok2 = ledger.reserve(
        CostReservationV1(
            reservation_id=uuid.uuid4(),
            campaign_id=cid,
            reserved_usd_micros=usd_to_micros("0.08"),
            reason="provision",
        )
    )
    assert ok1 is True
    assert ok2 is False


def test_example_g_unknown_network_component():
    snap = GhostCostLedger().campaign_snapshot("x")
    assert snap.total_final_usd_micros is None
    assert "no metered resources yet" in snap.unknown_components


def test_duplicate_termination_idempotent():
    ledger = GhostCostLedger()
    rid = str(uuid.uuid4())
    ps = uuid.uuid4()
    rec = ResourceCostRecordV1(
        resource_id=rid,
        product="cloud_compute",
        price_snapshot_id=ps,
        lifecycle=ResourceLifecycleTimestampsV1(),
    )
    ledger.register_resource(rec, hourly_rate_usd_micros=usd_to_micros("0.10"), event_id="e1")
    ledger.finalize_resource(rid, provider_lifetime_seconds=600, hourly_rate_usd="0.10", event_id="term-1")
    first = ledger.campaign_snapshot("c").total_known_usd_micros
    ledger.finalize_resource(rid, provider_lifetime_seconds=600, hourly_rate_usd="0.10", event_id="term-1")
    assert ledger.campaign_snapshot("c").total_known_usd_micros == first
