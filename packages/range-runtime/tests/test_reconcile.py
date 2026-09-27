"""Reconciliation tests: DB truth vs. provider truth.

Uses a small fixed-response ``StubProvider`` for the scenarios that need
an exact, unchanging provider answer (VANISHED, anomaly), and the real
``FakeComputeProvider`` (queried directly, ahead of what the engine
itself has observed) for the "DB is behind, walk it forward" scenario —
this is exactly the situation reconciliation exists for: something else
(a direct poll, a restart, a second process) learned the provider had
moved further than our last recorded transition.
"""

from __future__ import annotations

from ghostrange_contracts.enums import RangeLifecycleState

from ghostrange_range_runtime.provider import ProviderObservation, ProviderState
from ghostrange_range_runtime.reconcile import ReconcileAction, Reconciler


class StubProvider:
    def __init__(self, observation: ProviderObservation) -> None:
        self.observation = observation
        self.start_destroy_calls: list[tuple] = []

    def start_provisioning(self, **kwargs):
        raise AssertionError("not expected to be called in reconcile tests")

    def get_state(self, *, range_id, world_id):
        return self.observation

    def start_destroy(self, *, range_id, world_id, correlation_id):
        self.start_destroy_calls.append((range_id, world_id, correlation_id))


def test_reconcile_skips_terminal_ranges_without_consulting_provider(engine, spec):
    class ExplodingProvider(StubProvider):
        def get_state(self, *, range_id, world_id):
            raise AssertionError("terminal Range must never consult the provider")

    r = engine.create_range(spec, requested_by="c")
    r = engine.validate_and_authorize(r, spec)
    r = engine.fail(r, reason="forced for test", cleanup=False)
    assert r.status == RangeLifecycleState.FAILED

    engine.provider = ExplodingProvider(ProviderObservation(state=ProviderState.READY))
    outcome = Reconciler(engine).reconcile_one(r)

    assert outcome.action == ReconcileAction.SKIPPED_TERMINAL


def test_reconcile_skips_range_with_no_root_world_yet(engine, spec):
    r = engine.create_range(spec, requested_by="c")
    assert r.root_world_id is None

    outcome = Reconciler(engine).reconcile_one(r)
    assert outcome.action == ReconcileAction.SKIPPED_NOT_YET_PROVISIONED


def test_reconcile_no_op_when_db_and_provider_agree(engine, spec):
    r = engine.create_range(spec, requested_by="c")
    r = engine.validate_and_authorize(r, spec)
    r = engine.provision(r, spec)
    r = engine.run_provisioning_to_ready(r)
    assert r.status == RangeLifecycleState.READY

    engine.provider = StubProvider(ProviderObservation(state=ProviderState.READY))
    outcome = Reconciler(engine).reconcile_one(r)

    assert outcome.action == ReconcileAction.NO_OP
    assert outcome.range_record.status == RangeLifecycleState.READY


def test_reconcile_marks_failed_when_resource_vanished(engine, store, spec):
    r = engine.create_range(spec, requested_by="c")
    r = engine.validate_and_authorize(r, spec)
    r = engine.provision(r, spec)
    r = engine.run_provisioning_to_ready(r)
    r = engine.start_execution(r)
    assert r.status == RangeLifecycleState.EXECUTING

    engine.provider = StubProvider(ProviderObservation(state=ProviderState.VANISHED))
    outcome = Reconciler(engine).reconcile_one(r)

    assert outcome.action == ReconcileAction.MARKED_FAILED
    assert outcome.range_record.status == RangeLifecycleState.FAILED
    assert "VANISHED" in outcome.range_record.failure_reason
    assert store.latest_state(r.id) == RangeLifecycleState.FAILED


def test_reconcile_walks_forward_through_legal_intermediate_states(engine, store, spec):
    r = engine.create_range(spec, requested_by="c")
    r = engine.validate_and_authorize(r, spec)
    r = engine.provision(r, spec)
    assert r.status == RangeLifecycleState.PROVISIONING

    # The provider has already moved on to READY (e.g. observed by a
    # different process / a direct poll) — the engine's own DB record
    # doesn't know that yet.
    provider = engine.provider
    for _ in range(3):
        provider.get_state(range_id=r.id, world_id=r.root_world_id)

    outcome = Reconciler(engine).reconcile_one(r)

    assert outcome.action == ReconcileAction.ADVANCED
    assert outcome.range_record.status == RangeLifecycleState.READY

    history = store.history(r.id)
    new_states = [h.new_state for h in history]
    # PROVISIONING -> BOOTING -> READY, in order, never skipping BOOTING.
    assert new_states[-2:] == [RangeLifecycleState.BOOTING, RangeLifecycleState.READY]


def test_reconcile_anomaly_when_provider_is_behind_an_internal_phase(engine, spec):
    r = engine.create_range(spec, requested_by="c")
    r = engine.validate_and_authorize(r, spec)
    r = engine.provision(r, spec)
    r = engine.run_provisioning_to_ready(r)
    r = engine.start_execution(r)
    assert r.status == RangeLifecycleState.EXECUTING

    # EXECUTING is a range-runtime-internal phase; no legal *forward*
    # path exists from EXECUTING back down to PROVISIONING, so this must
    # be reported, not silently "corrected."
    engine.provider = StubProvider(ProviderObservation(state=ProviderState.PROVISIONING))
    outcome = Reconciler(engine).reconcile_one(r)

    assert outcome.action == ReconcileAction.ANOMALY
    assert outcome.range_record.status == RangeLifecycleState.EXECUTING, "must not mutate on anomaly"


def test_reconcile_all_batches_multiple_ranges(engine, spec):
    r1 = engine.create_range(spec, requested_by="c")
    r2 = engine.create_range(spec, requested_by="c")

    outcomes = Reconciler(engine).reconcile_all([r1, r2])
    assert {o.range_id for o in outcomes} == {r1.id, r2.id}
    assert all(o.action == ReconcileAction.SKIPPED_NOT_YET_PROVISIONED for o in outcomes)
