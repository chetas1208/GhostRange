"""Proves RealVultrProvider and MockVultrProvider are interchangeable behind
VultrControlProvider: the same abstract methods exist on both, and the same
workflow produces analogous outcomes on both (mock instantly, real against a
stateful HTTP fake). This is what lets packages/range-runtime and
packages/range-iac depend on the interface, not on a specific
implementation.
"""

from __future__ import annotations

import inspect

import httpx
import pytest

from ghostrange_vultr_control import (
    CreateComputeRequest,
    CreateWorldRequest,
    GhostRangeTags,
    MockVultrProvider,
    ProviderKind,
    RealVultrProvider,
    ResourceStatus,
    VultrControlProvider,
)
from ghostrange_vultr_control.errors import VultrNotFoundError
from ghostrange_vultr_control.http_client import VultrHTTPClient

from fake_vultr_server import FakeVultrServer

FAKE_KEY = "sk-test-not-a-real-vultr-key-0000000000"


def make_real_provider() -> RealVultrProvider:
    server = FakeVultrServer()
    http_client = VultrHTTPClient(
        api_key=FAKE_KEY, transport=httpx.MockTransport(server.handler), requests_per_second=10_000
    )
    provider = RealVultrProvider(http_client=http_client)
    provider._test_fake_server = server  # type: ignore[attr-defined]
    return provider


def test_both_implementations_expose_the_same_abstract_methods():
    abstract_methods = VultrControlProvider.__abstractmethods__
    for method_name in abstract_methods:
        assert hasattr(RealVultrProvider, method_name)
        assert hasattr(MockVultrProvider, method_name)
        real_sig = inspect.signature(getattr(RealVultrProvider, method_name))
        mock_sig = inspect.signature(getattr(MockVultrProvider, method_name))
        assert list(real_sig.parameters) == list(mock_sig.parameters), method_name


@pytest.fixture(params=["mock", "real"])
def provider(request, monkeypatch):
    monkeypatch.setattr("ghostrange_vultr_control.real_provider.time.sleep", lambda _s: None)
    monkeypatch.setattr("ghostrange_vultr_control.http_client.time.sleep", lambda _s: None)
    if request.param == "mock":
        return MockVultrProvider()
    return make_real_provider()


class TestSharedWorkflow:
    def test_full_world_and_compute_lifecycle(self, provider):
        tags = GhostRangeTags(range_id="range-1", world_id="world-1")

        world = provider.create_world(CreateWorldRequest(region="ewr", tags=tags))
        assert world.status == ResourceStatus.ACTIVE
        assert world.provider in (ProviderKind.MOCK, ProviderKind.VULTR)

        fetched_world = provider.get_world(world.provider_world_id)
        assert fetched_world.provider_world_id == world.provider_world_id

        compute = provider.create_compute(
            CreateComputeRequest(world_ref=world.provider_world_id, region="ewr", plan="vc2-1c-1gb", tags=tags, os_id=387)
        )
        assert compute.world_ref == world.provider_world_id

        # The fake Vultr HTTP server starts instances "pending" just like the
        # real API would; MockVultrProvider defaults to instant=True (already
        # active). Nudge the fake server so both branches of this
        # parametrized test reach ACTIVE without an artificial real timeout.
        fake_server = getattr(provider, "_test_fake_server", None)
        if fake_server is not None:
            fake_server.mark_active(compute.provider_compute_id)

        ready = provider.wait_until_ready(compute.provider_compute_id, timeout_s=5, poll_interval_s=0)
        assert ready.status == ResourceStatus.ACTIVE

        listed = provider.list_computes(range_id="range-1")
        assert compute.provider_compute_id in {c.provider_compute_id for c in listed}

        provider.destroy_compute(compute.provider_compute_id, timeout_s=5, poll_interval_s=0)
        with pytest.raises(VultrNotFoundError):
            provider.get_compute(compute.provider_compute_id)

        provider.destroy_world(world.provider_world_id, firewall_group_id=world.firewall_group_id, timeout_s=5, poll_interval_s=0)
        with pytest.raises(VultrNotFoundError):
            provider.get_world(world.provider_world_id)

    def test_create_compute_rejects_unknown_world(self, provider):
        tags = GhostRangeTags(range_id="range-1")
        from ghostrange_vultr_control.errors import VultrControlError

        with pytest.raises(VultrControlError):
            provider.create_compute(
                CreateComputeRequest(world_ref="does-not-exist", region="ewr", plan="vc2-1c-1gb", tags=tags, os_id=387)
            )

    def test_fork_path_uses_snapshot_id(self, provider):
        tags = GhostRangeTags(range_id="range-1")
        world = provider.create_world(CreateWorldRequest(region="ewr", tags=tags))
        compute = provider.create_compute(
            CreateComputeRequest(
                world_ref=world.provider_world_id, region="ewr", plan="vc2-1c-1gb", tags=tags, snapshot_id="snap-golden-1"
            )
        )
        assert compute.provider_compute_id


class TestOwnershipFiltering:
    """The security-critical invariant `list_computes()` (and everything
    built on it — `list_owned_workers`, `list_all_ghostrange_workers`,
    ShieldedComputeProvider's ownership check) depends on: an instance
    with no parseable GhostRange tags must never be returned, whether the
    caller asked for a specific range or for every GhostRange-owned
    instance (`range_id=None`).

    A foreign/untagged instance can't be produced through this package's
    own `create_compute()` (GhostRangeTags.range_id is required), so it's
    injected directly into the provider's backing store here — modeling a
    hand-created VM, or one belonging to a different tool/account, sitting
    in the same Vultr account as GhostRange-owned resources.
    """

    @staticmethod
    def _inject_untagged_instance(provider, instance_id: str) -> None:
        fake_server = getattr(provider, "_test_fake_server", None)
        if fake_server is not None:
            fake_server.instances[instance_id] = {
                "id": instance_id,
                "region": "ewr",
                "plan": "vc2-1c-1gb",
                "main_ip": "203.0.113.250",
                "status": "active",
                "power_status": "running",
                "server_status": "ok",
                "os_id": 387,
                "snapshot_id": "",
                "firewall_group_id": "",
                "hostname": "hand-created-vm",
                "label": "not-ours",
                "tags": [],  # no ghostrange:* tags at all
                "date_created": "2026-09-26T00:00:00+00:00",
            }
            return
        from ghostrange_vultr_control.models import ComputeRecord

        provider._computes[instance_id] = ComputeRecord(  # noqa: SLF001 - test-only injection
            provider=ProviderKind.MOCK,
            provider_compute_id=instance_id,
            region="ewr",
            plan="vc2-1c-1gb",
            status=ResourceStatus.ACTIVE,
            tags=None,
        )

    def test_untagged_instance_never_appears_when_range_id_is_none(self, provider):
        tags = GhostRangeTags(range_id="range-1")
        world = provider.create_world(CreateWorldRequest(region="ewr", tags=tags))
        owned = provider.create_compute(
            CreateComputeRequest(world_ref=world.provider_world_id, region="ewr", plan="vc2-1c-1gb", tags=tags, os_id=387)
        )
        self._inject_untagged_instance(provider, "foreign-instance-none-filter")

        all_owned = provider.list_computes(range_id=None)
        ids = {c.provider_compute_id for c in all_owned}
        assert owned.provider_compute_id in ids
        assert "foreign-instance-none-filter" not in ids

    def test_untagged_instance_never_appears_for_a_specific_range_id(self, provider):
        tags = GhostRangeTags(range_id="range-1")
        world = provider.create_world(CreateWorldRequest(region="ewr", tags=tags))
        owned = provider.create_compute(
            CreateComputeRequest(world_ref=world.provider_world_id, region="ewr", plan="vc2-1c-1gb", tags=tags, os_id=387)
        )
        self._inject_untagged_instance(provider, "foreign-instance-specific-filter")

        filtered = provider.list_computes(range_id="range-1")
        ids = {c.provider_compute_id for c in filtered}
        assert owned.provider_compute_id in ids
        assert "foreign-instance-specific-filter" not in ids

    def test_other_range_tagged_instance_excluded_from_specific_range_filter(self, provider):
        tags_a = GhostRangeTags(range_id="range-a")
        tags_b = GhostRangeTags(range_id="range-b")
        world_a = provider.create_world(CreateWorldRequest(region="ewr", tags=tags_a))
        world_b = provider.create_world(CreateWorldRequest(region="ewr", tags=tags_b))
        compute_a = provider.create_compute(
            CreateComputeRequest(world_ref=world_a.provider_world_id, region="ewr", plan="vc2-1c-1gb", tags=tags_a, os_id=387)
        )
        compute_b = provider.create_compute(
            CreateComputeRequest(world_ref=world_b.provider_world_id, region="ewr", plan="vc2-1c-1gb", tags=tags_b, os_id=387)
        )

        filtered = provider.list_computes(range_id="range-a")
        ids = {c.provider_compute_id for c in filtered}
        assert compute_a.provider_compute_id in ids
        assert compute_b.provider_compute_id not in ids
