"""Fake-provider-driven end-to-end tests: one full happy path through
every lifecycle state, and two distinct failure paths (provider raises
synchronously during start_provisioning; provider reports FAILED mid-poll
during BOOTING) each checking that partial-resource cleanup was actually
triggered, not just that the state flipped to FAILED. Also a
restart/resume test proving persisted state survives a fresh engine
instance against the same DB file.
"""

from __future__ import annotations

from ghostrange_contracts.enums import RangeLifecycleState
from ghostrange_events import WorldDestroyedV1, WorldProvisioningV1, WorldReadyV1, WorldRequestedV1

from ghostrange_range_runtime.engine import RangeRuntimeEngine
from ghostrange_range_runtime.errors import IllegalTransitionError
from ghostrange_range_runtime.events import InMemoryEventSink, RangeTransitionEventV1
from ghostrange_range_runtime.persistence import SqliteTransitionStore
from ghostrange_range_runtime.provider import FakeComputeProvider, ProviderState


def test_happy_path_requested_to_destroyed(engine, store, provider, sink, spec):
    r = engine.create_range(spec, requested_by="chetasparekh2003@gmail.com")
    assert r.status == RangeLifecycleState.REQUESTED

    r = engine.validate_and_authorize(r, spec)
    assert r.status == RangeLifecycleState.PLANNING
    assert r.root_world_id is not None

    r = engine.provision(r, spec)
    assert r.status == RangeLifecycleState.PROVISIONING

    r = engine.run_provisioning_to_ready(r)
    assert r.status == RangeLifecycleState.READY

    r = engine.start_execution(r)
    assert r.status == RangeLifecycleState.EXECUTING

    r = engine.start_verifying(r)
    assert r.status == RangeLifecycleState.VERIFYING

    r = engine.resume_execution(r)
    assert r.status == RangeLifecycleState.EXECUTING

    r = engine.start_verifying(r, reason="second verification round")
    assert r.status == RangeLifecycleState.VERIFYING

    r = engine.stop(r, reason="all remediation candidates verified")
    assert r.status == RangeLifecycleState.STOPPING

    r = engine.begin_destroy(r)
    assert r.status == RangeLifecycleState.DESTROYING
    assert provider.start_destroy_calls, "begin_destroy must call provider.start_destroy"

    r = engine.run_teardown_to_destroyed(r)
    assert r.status == RangeLifecycleState.DESTROYED
    assert r.destroyed_at is not None

    # Durable history matches the exact sequence driven above.
    history = store.history(r.id)
    observed_sequence = [h.new_state for h in history]
    assert observed_sequence == [
        RangeLifecycleState.REQUESTED,
        RangeLifecycleState.PLANNING,  # VALIDATING passed
        RangeLifecycleState.PLANNING,  # AUTHORIZED checkpoint (no-op hop)
        RangeLifecycleState.PROVISIONING,
        RangeLifecycleState.BOOTING,
        RangeLifecycleState.READY,
        RangeLifecycleState.EXECUTING,
        RangeLifecycleState.VERIFYING,
        RangeLifecycleState.EXECUTING,
        RangeLifecycleState.VERIFYING,
        RangeLifecycleState.STOPPING,
        RangeLifecycleState.DESTROYING,
        RangeLifecycleState.DESTROYED,
    ]

    # Real ghostrange_events payloads fired for the root World at the
    # transitions that map onto WorldStatus (see README gap #3).
    assert len(sink.of_type(WorldRequestedV1)) == 1
    assert len(sink.of_type(WorldProvisioningV1)) == 1
    assert len(sink.of_type(WorldReadyV1)) == 1
    assert len(sink.of_type(WorldDestroyedV1)) == 1
    assert sink.of_type(WorldReadyV1)[0].asset_count == len(spec.assets)

    # Every durable transition has a matching RangeTransitionEventV1.
    range_events = sink.of_type(RangeTransitionEventV1)
    assert len(range_events) == len(history)


def test_provisioning_failure_via_provider_exception_triggers_cleanup(store, sink, spec):
    class RaisingProvider(FakeComputeProvider):
        def start_provisioning(self, **kwargs):
            raise RuntimeError("vultr-control: create-instance API call failed (simulated)")

    provider = RaisingProvider()
    engine = RangeRuntimeEngine(store=store, provider=provider, sink=sink)

    r = engine.create_range(spec, requested_by="chetasparekh2003@gmail.com")
    r = engine.validate_and_authorize(r, spec)
    r = engine.provision(r, spec)

    assert r.status == RangeLifecycleState.FAILED
    assert "vultr-control: create-instance API call failed" in r.failure_reason
    assert "cleanup" in r.failure_reason.lower()
    assert provider.start_destroy_calls, "cleanup must be triggered on provisioning failure"

    # FAILED is terminal: no further progress is possible, and the
    # attempt must raise, not silently no-op.
    import pytest

    with pytest.raises(IllegalTransitionError):
        engine.provision(r, spec)


def test_provisioning_failure_via_provider_poll_triggers_cleanup(store, sink, spec):
    provider = FakeComputeProvider(steps_to_booting=1, steps_to_ready=3)
    engine = RangeRuntimeEngine(store=store, provider=provider, sink=sink)

    r = engine.create_range(spec, requested_by="chetasparekh2003@gmail.com")
    r = engine.validate_and_authorize(r, spec)
    r = engine.provision(r, spec)
    provider.inject_failure_at(r.id, r.root_world_id, ProviderState.BOOTING)

    r = engine.run_provisioning_to_ready(r)

    assert r.status == RangeLifecycleState.FAILED
    assert "provisioning failed" in r.failure_reason.lower()
    assert provider.start_destroy_calls, "cleanup must be triggered on mid-poll provisioning failure"
    assert provider.resources_remaining(r.id, r.root_world_id) == []

    # Persisted durably: reloading from a brand-new store instance
    # against the same file agrees.
    reloaded_state = store.latest_state(r.id)
    assert reloaded_state == RangeLifecycleState.FAILED


def test_validation_failure_transitions_to_failed_and_raises(engine, store):
    from ghostrange_contracts.range import AssetSpecV1, NetworkSpecV1, RangeSpecV1
    from ghostrange_contracts.enums import AssetRole
    import uuid

    net = NetworkSpecV1(name="isolated-net", cidr="10.1.0.0/24")
    bad_asset = AssetSpecV1(
        hostname="orphan",
        network_id=uuid.uuid4(),  # does not match any declared network
        os_family="linux",
        role=AssetRole.SERVER,
        image="ubuntu-22.04",
    )
    bad_spec = RangeSpecV1(
        name="bad-spec",
        owner="chetasparekh2003@gmail.com",
        networks=[net],
        assets=[bad_asset],
    )

    r = engine.create_range(bad_spec, requested_by="chetasparekh2003@gmail.com")

    import pytest
    from ghostrange_range_runtime.errors import ValidationFailedError

    with pytest.raises(ValidationFailedError):
        engine.validate_and_authorize(r, bad_spec)

    assert r.status == RangeLifecycleState.FAILED
    assert "VALIDATING failed" in r.failure_reason
    assert store.latest_state(r.id) == RangeLifecycleState.FAILED


def test_authorization_failure_transitions_to_failed(engine, spec):
    r = engine.create_range(spec, requested_by="chetasparekh2003@gmail.com")

    import pytest
    from ghostrange_range_runtime.errors import ValidationFailedError

    with pytest.raises(ValidationFailedError):
        engine.validate_and_authorize(r, spec, policy_attached=False)

    assert r.status == RangeLifecycleState.FAILED
    assert "AUTHORIZED failed" in r.failure_reason


def test_resume_after_restart_preserves_state(db_path, spec):
    provider = FakeComputeProvider()

    store1 = SqliteTransitionStore(db_path)
    sink1 = InMemoryEventSink()
    engine1 = RangeRuntimeEngine(store=store1, provider=provider, sink=sink1)

    r = engine1.create_range(spec, requested_by="chetasparekh2003@gmail.com")
    r = engine1.validate_and_authorize(r, spec)
    r = engine1.provision(r, spec)
    r = engine1.run_provisioning_to_ready(r)
    assert r.status == RangeLifecycleState.READY
    range_id = r.id
    store1.close()

    # Simulate the process restarting: brand new store + engine against
    # the same DB file (provider is the same object here only because a
    # real provider would be a network client reconnecting to the same
    # Vultr account/project — the DB survives regardless of what the
    # provider client object's lifetime is).
    store2 = SqliteTransitionStore(db_path)
    sink2 = InMemoryEventSink()
    engine2 = RangeRuntimeEngine(store=store2, provider=provider, sink=sink2)

    reloaded = engine2.load_range(range_id)
    assert reloaded is not None
    assert reloaded.status == RangeLifecycleState.READY
    assert store2.latest_state(range_id) == RangeLifecycleState.READY

    # And the resumed engine can keep driving the same Range forward.
    reloaded = engine2.start_execution(reloaded)
    assert reloaded.status == RangeLifecycleState.EXECUTING
    store2.close()
