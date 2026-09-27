from __future__ import annotations

import pytest

from ghostrange_vultr_control import (
    GhostRangeTags,
    MockVultrProvider,
    ProviderKind,
    ResourceStatus,
    WorldRecord,
)
from ghostrange_vultr_control.errors import VultrNotFoundError, VultrTimeoutError, VultrValidationError

from vultr_test_helpers import make_compute_req


class TestWorldLifecycle:
    def test_create_world_returns_mock_provider_tag(self, world_req):
        p = MockVultrProvider()
        w = p.create_world(world_req)
        assert w.provider == ProviderKind.MOCK
        assert w.provider_world_id == "mock-vpc-1"
        assert w.status == ResourceStatus.ACTIVE
        assert w.tags == world_req.tags

    def test_create_world_creates_paired_firewall_group_by_default(self, world_req):
        p = MockVultrProvider()
        w = p.create_world(world_req)
        assert w.firewall_group_id == "mock-fwg-1"

    def test_create_world_can_skip_firewall_group(self, tags):
        from ghostrange_vultr_control import CreateWorldRequest

        p = MockVultrProvider()
        w = p.create_world(CreateWorldRequest(region="ewr", tags=tags, create_firewall_group=False))
        assert w.firewall_group_id is None

    def test_ids_are_sequential_and_deterministic_per_instance(self, world_req):
        p = MockVultrProvider()
        w1 = p.create_world(world_req)
        w2 = p.create_world(world_req)
        assert w1.provider_world_id == "mock-vpc-1"
        assert w2.provider_world_id == "mock-vpc-2"

        p2 = MockVultrProvider()
        w3 = p2.create_world(world_req)
        assert w3.provider_world_id == "mock-vpc-1"  # fresh provider, counters reset

    def test_get_world_returns_same_record(self, world_req):
        p = MockVultrProvider()
        w = p.create_world(world_req)
        fetched = p.get_world(w.provider_world_id)
        assert fetched == w

    def test_get_world_missing_raises_not_found(self):
        p = MockVultrProvider()
        with pytest.raises(VultrNotFoundError):
            p.get_world("mock-vpc-does-not-exist")

    def test_destroy_world_then_get_raises_not_found(self, world_req):
        p = MockVultrProvider()
        w = p.create_world(world_req)
        p.destroy_world(w.provider_world_id)
        with pytest.raises(VultrNotFoundError):
            p.get_world(w.provider_world_id)

    def test_destroy_world_missing_raises_not_found(self):
        p = MockVultrProvider()
        with pytest.raises(VultrNotFoundError):
            p.destroy_world("mock-vpc-does-not-exist")

    def test_list_worlds_filters_by_range_id(self, tags):
        from ghostrange_vultr_control import CreateWorldRequest

        p = MockVultrProvider()
        other_tags = GhostRangeTags(range_id="range-2")
        w1 = p.create_world(CreateWorldRequest(region="ewr", tags=tags))
        w2 = p.create_world(CreateWorldRequest(region="ewr", tags=other_tags))

        all_worlds = p.list_worlds()
        assert {w.provider_world_id for w in all_worlds} == {w1.provider_world_id, w2.provider_world_id}

        range1_worlds = p.list_worlds(range_id="range-1")
        assert [w.provider_world_id for w in range1_worlds] == [w1.provider_world_id]

    def test_list_worlds_excludes_untagged_when_range_id_none(self):
        """Untagged VPCs must not appear in default list (M2 security)."""
        p = MockVultrProvider()
        p._worlds["mock-vpc-orphan"] = WorldRecord(
            provider=ProviderKind.MOCK,
            provider_world_id="mock-vpc-orphan",
            region="ewr",
            status=ResourceStatus.ACTIVE,
            tags=None,
        )
        ids = {w.provider_world_id for w in p.list_worlds()}
        assert "mock-vpc-orphan" not in ids


class TestComputeLifecycle:
    def test_create_compute_requires_existing_world(self, tags):
        p = MockVultrProvider()
        with pytest.raises(VultrValidationError):
            p.create_compute(make_compute_req("mock-vpc-nonexistent", tags))

    def test_create_compute_returns_mock_provider_tag(self, world_req, tags):
        p = MockVultrProvider()
        w = p.create_world(world_req)
        c = p.create_compute(make_compute_req(w.provider_world_id, tags))
        assert c.provider == ProviderKind.MOCK
        assert c.provider_compute_id == "mock-instance-1"
        assert c.world_ref == w.provider_world_id
        assert c.tags == tags

    def test_instant_mode_compute_is_immediately_active(self, world_req, tags):
        p = MockVultrProvider(instant=True)
        w = p.create_world(world_req)
        c = p.create_compute(make_compute_req(w.provider_world_id, tags))
        assert c.status == ResourceStatus.ACTIVE

    def test_get_compute_missing_raises_not_found(self):
        p = MockVultrProvider()
        with pytest.raises(VultrNotFoundError):
            p.get_compute("mock-instance-does-not-exist")

    def test_wait_until_ready_instant_mode_returns_immediately(self, world_req, tags):
        p = MockVultrProvider(instant=True)
        w = p.create_world(world_req)
        c = p.create_compute(make_compute_req(w.provider_world_id, tags))
        ready = p.wait_until_ready(c.provider_compute_id, timeout_s=1, poll_interval_s=0.01)
        assert ready.status == ResourceStatus.ACTIVE

    def test_non_instant_mode_becomes_ready_after_boot_delay(self, world_req, tags):
        p = MockVultrProvider(instant=False, boot_delay_s=0.05)
        w = p.create_world(world_req)
        c = p.create_compute(make_compute_req(w.provider_world_id, tags))
        assert c.status == ResourceStatus.PENDING

        ready = p.wait_until_ready(c.provider_compute_id, timeout_s=2, poll_interval_s=0.01)
        assert ready.status == ResourceStatus.ACTIVE
        assert ready.vultr_power_status == "running"
        assert ready.vultr_server_status == "ok"

    def test_wait_until_ready_times_out_when_budget_too_short(self, world_req, tags):
        p = MockVultrProvider(instant=False, boot_delay_s=10.0)
        w = p.create_world(world_req)
        c = p.create_compute(make_compute_req(w.provider_world_id, tags))
        with pytest.raises(VultrTimeoutError):
            p.wait_until_ready(c.provider_compute_id, timeout_s=0.05, poll_interval_s=0.01)

    def test_destroy_compute_instant_then_get_raises_not_found(self, world_req, tags):
        p = MockVultrProvider(instant=True)
        w = p.create_world(world_req)
        c = p.create_compute(make_compute_req(w.provider_world_id, tags))
        p.destroy_compute(c.provider_compute_id)
        with pytest.raises(VultrNotFoundError):
            p.get_compute(c.provider_compute_id)

    def test_destroy_compute_missing_raises_not_found(self):
        p = MockVultrProvider()
        with pytest.raises(VultrNotFoundError):
            p.destroy_compute("mock-instance-does-not-exist")

    def test_destroy_compute_confirms_deletion_after_delay(self, world_req, tags):
        p = MockVultrProvider(instant=False, delete_delay_s=0.05)
        w = p.create_world(world_req)
        c = p.create_compute(make_compute_req(w.provider_world_id, tags))
        p.destroy_compute(c.provider_compute_id, timeout_s=2, poll_interval_s=0.01)
        with pytest.raises(VultrNotFoundError):
            p.get_compute(c.provider_compute_id)

    def test_destroy_compute_times_out_when_budget_too_short(self, world_req, tags):
        p = MockVultrProvider(instant=False, delete_delay_s=10.0)
        w = p.create_world(world_req)
        c = p.create_compute(make_compute_req(w.provider_world_id, tags))
        with pytest.raises(VultrTimeoutError):
            p.destroy_compute(c.provider_compute_id, timeout_s=0.05, poll_interval_s=0.01)

    def test_list_computes_filters_by_range_id(self, world_req, tags):
        p = MockVultrProvider()
        w = p.create_world(world_req)
        other_tags = GhostRangeTags(range_id="range-2")
        c1 = p.create_compute(make_compute_req(w.provider_world_id, tags))
        c2 = p.create_compute(make_compute_req(w.provider_world_id, other_tags))

        all_computes = p.list_computes()
        assert {c.provider_compute_id for c in all_computes} == {c1.provider_compute_id, c2.provider_compute_id}

        range1_computes = p.list_computes(range_id="range-1")
        assert [c.provider_compute_id for c in range1_computes] == [c1.provider_compute_id]

    def test_forked_compute_from_snapshot_id(self, world_req, tags):
        p = MockVultrProvider()
        w = p.create_world(world_req)
        c = p.create_compute(make_compute_req(w.provider_world_id, tags, os_id=None, snapshot_id="snap-golden-1"))
        assert c.provider == ProviderKind.MOCK
        assert c.status == ResourceStatus.ACTIVE


class TestNeverPretendsToBeLive:
    def test_every_world_and_compute_record_is_tagged_mock(self, world_req, tags):
        p = MockVultrProvider()
        w = p.create_world(world_req)
        c = p.create_compute(make_compute_req(w.provider_world_id, tags))
        assert w.provider is ProviderKind.MOCK
        assert c.provider is ProviderKind.MOCK
        assert p.get_world(w.provider_world_id).provider is ProviderKind.MOCK
        assert p.get_compute(c.provider_compute_id).provider is ProviderKind.MOCK
