from __future__ import annotations

import uuid

from ghostrange_range_runtime.provider import FakeComputeProvider, ProviderState


def test_unknown_before_provisioning():
    p = FakeComputeProvider()
    obs = p.get_state(range_id=uuid.uuid4(), world_id=uuid.uuid4())
    assert obs.state == ProviderState.UNKNOWN


def test_progression_provisioning_booting_ready(spec):
    p = FakeComputeProvider(steps_to_booting=1, steps_to_ready=2)
    rid, wid = uuid.uuid4(), uuid.uuid4()
    p.start_provisioning(range_id=rid, world_id=wid, spec=spec, correlation_id="c")

    assert p.get_state(range_id=rid, world_id=wid).state == ProviderState.PROVISIONING
    assert p.get_state(range_id=rid, world_id=wid).state == ProviderState.BOOTING
    assert p.get_state(range_id=rid, world_id=wid).state == ProviderState.READY
    # stays READY on further polls
    assert p.get_state(range_id=rid, world_id=wid).state == ProviderState.READY


def test_injected_failure_at_booting(spec):
    p = FakeComputeProvider(steps_to_booting=1, steps_to_ready=3)
    rid, wid = uuid.uuid4(), uuid.uuid4()
    p.start_provisioning(range_id=rid, world_id=wid, spec=spec, correlation_id="c")
    p.inject_failure_at(rid, wid, ProviderState.BOOTING)

    assert p.get_state(range_id=rid, world_id=wid).state == ProviderState.PROVISIONING
    obs = p.get_state(range_id=rid, world_id=wid)
    assert obs.state == ProviderState.FAILED


def test_destroy_lifecycle_and_resource_cleanup(spec):
    p = FakeComputeProvider(steps_to_destroyed=2)
    rid, wid = uuid.uuid4(), uuid.uuid4()
    p.start_provisioning(range_id=rid, world_id=wid, spec=spec, correlation_id="c")
    assert p.resources_remaining(rid, wid), "fake resources should exist after provisioning"

    p.start_destroy(range_id=rid, world_id=wid, correlation_id="c-destroy")
    assert p.get_state(range_id=rid, world_id=wid).state == ProviderState.DESTROYING
    obs = p.get_state(range_id=rid, world_id=wid)
    assert obs.state == ProviderState.DESTROYED
    assert p.resources_remaining(rid, wid) == []
    assert p.start_destroy_calls[-1][:2] == (str(rid), str(wid))


def test_destroy_with_no_resources_is_immediate_noop():
    p = FakeComputeProvider()
    rid, wid = uuid.uuid4(), uuid.uuid4()
    p.start_destroy(range_id=rid, world_id=wid, correlation_id="c")
    assert p.get_state(range_id=rid, world_id=wid).state == ProviderState.DESTROYED
