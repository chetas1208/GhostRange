"""Real two-package integration test: RangeRuntimeEngine driven against
an actual ``ghostrange_vultr_control.MockVultrProvider`` (not this
package's own ``FakeComputeProvider``), through the
``VultrAdaptedComputeProvider`` glue in ``vultr_adapter.py``. This is the
concrete proof that the "coordinate via the interface" plan in
provider.py/README actually composes with what Agent 02 shipped, not
just a documented intent.
"""

from __future__ import annotations

from ghostrange_contracts.enums import RangeLifecycleState
from ghostrange_vultr_control import MockVultrProvider

from ghostrange_range_runtime.engine import RangeRuntimeEngine
from ghostrange_range_runtime.events import InMemoryEventSink
from ghostrange_range_runtime.vultr_adapter import VultrAdaptedComputeProvider


def test_happy_path_against_real_mock_vultr_provider(store, spec):
    vultr = MockVultrProvider(instant=True)
    provider = VultrAdaptedComputeProvider(vultr)
    sink = InMemoryEventSink()
    engine = RangeRuntimeEngine(store=store, provider=provider, sink=sink)

    r = engine.create_range(spec, requested_by="chetasparekh2003@gmail.com")
    r = engine.validate_and_authorize(r, spec)
    r = engine.provision(r, spec)
    assert r.status == RangeLifecycleState.PROVISIONING

    r = engine.run_provisioning_to_ready(r)
    assert r.status == RangeLifecycleState.READY

    # Real VultrControlProvider-side records actually exist.
    live_computes = vultr.list_computes()
    assert len(live_computes) == len(spec.assets)
    live_worlds = vultr.list_worlds(range_id=str(r.id))
    assert len(live_worlds) == 1

    r = engine.start_execution(r)
    r = engine.stop(r, reason="done")
    r = engine.begin_destroy(r)
    r = engine.run_teardown_to_destroyed(r)
    assert r.status == RangeLifecycleState.DESTROYED

    # And the real provider confirms the resources are actually gone.
    assert vultr.list_computes() == []
    assert vultr.list_worlds() == []


def test_provisioning_failure_when_world_ref_missing_is_surfaced(store, spec):
    """create_compute against a MockVultrProvider that never got a
    matching create_world call (simulated by destroying the world out
    from under the adapter) surfaces as a FAILED provider observation,
    not an uncaught exception escaping the engine.
    """
    vultr = MockVultrProvider(instant=True)
    provider = VultrAdaptedComputeProvider(vultr)
    sink = InMemoryEventSink()
    engine = RangeRuntimeEngine(store=store, provider=provider, sink=sink)

    r = engine.create_range(spec, requested_by="chetasparekh2003@gmail.com")
    r = engine.validate_and_authorize(r, spec)

    # Sabotage: remove the world the adapter is about to reference by
    # pre-destroying anything it creates, via a wrapped provider whose
    # create_world succeeds but whose create_compute always sees a
    # world that's already gone (simulates a race/out-of-band deletion).
    real_create_world = vultr.create_world

    def create_world_then_delete(req):
        record = real_create_world(req)
        vultr._worlds.pop(record.provider_world_id, None)  # noqa: SLF001 - test sabotage
        return record

    vultr.create_world = create_world_then_delete  # type: ignore[method-assign]

    r = engine.provision(r, spec)
    r = engine.run_provisioning_to_ready(r)

    assert r.status == RangeLifecycleState.FAILED
    assert "create_compute failed" in r.failure_reason
