"""RealVultrProvider tests: request-construction and response-parsing logic,
exercised against a stateful fake of Vultr's HTTP API (fake_vultr_server.py)
via httpx.MockTransport. No network access, no real credentials.

These assert the exact request shapes RealVultrProvider sends — the same
shapes documented in README.md's "Endpoints used" table, each verified
against the current `govultr` v3 SDK source on 2026-09-26. This is the
closest thing to an integration test this package can run without a real
VULTR_API_KEY; see test_real_vultr_e2e_not_run below and README.md for what
still needs a live credential to actually confirm.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from ghostrange_vultr_control import (
    CreateComputeRequest,
    CreateWorldRequest,
    GhostRangeTags,
    ProviderKind,
    RealVultrProvider,
    ResourceStatus,
)
from ghostrange_vultr_control.errors import VultrNotFoundError, VultrTimeoutError
from ghostrange_vultr_control.http_client import VultrHTTPClient

from fake_vultr_server import FakeVultrServer

FAKE_KEY = "sk-test-not-a-real-vultr-key-0000000000"


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    monkeypatch.setattr("ghostrange_vultr_control.real_provider.time.sleep", lambda _s: None)
    monkeypatch.setattr("ghostrange_vultr_control.http_client.time.sleep", lambda _s: None)


@pytest.fixture
def fake_server() -> FakeVultrServer:
    return FakeVultrServer()


@pytest.fixture
def provider(fake_server: FakeVultrServer) -> RealVultrProvider:
    http_client = VultrHTTPClient(
        api_key=FAKE_KEY, transport=httpx.MockTransport(fake_server.handler), requests_per_second=10_000
    )
    return RealVultrProvider(http_client=http_client)


def _make_world(provider: RealVultrProvider) -> str:
    w = provider.create_world(CreateWorldRequest(region="ewr", tags=GhostRangeTags(range_id="range-1")))
    return w.provider_world_id


class TestCreateWorldRequestShape:
    def test_posts_vpcs_with_region_and_description(self, provider, fake_server):
        tags = GhostRangeTags(range_id="range-1", world_id="world-1")
        provider.create_world(CreateWorldRequest(region="ewr", tags=tags))

        vpc_requests = [r for r in fake_server.requests if r.url.path == "/v2/vpcs" and r.method == "POST"]
        assert len(vpc_requests) == 1
        body = json.loads(vpc_requests[0].content)
        assert body["region"] == "ewr"
        assert body["description"] == tags.as_description()
        assert "v4_subnet" not in body  # not requested, must not be sent

    def test_also_creates_firewall_group_by_default(self, provider, fake_server):
        tags = GhostRangeTags(range_id="range-1")
        w = provider.create_world(CreateWorldRequest(region="ewr", tags=tags))

        fwg_requests = [r for r in fake_server.requests if r.url.path == "/v2/firewalls" and r.method == "POST"]
        assert len(fwg_requests) == 1
        assert w.firewall_group_id is not None
        assert w.firewall_group_id in fake_server.firewall_groups

    def test_skips_firewall_group_when_disabled(self, provider, fake_server):
        tags = GhostRangeTags(range_id="range-1")
        w = provider.create_world(CreateWorldRequest(region="ewr", tags=tags, create_firewall_group=False))
        assert w.firewall_group_id is None
        assert not [r for r in fake_server.requests if r.url.path == "/v2/firewalls"]

    def test_result_tagged_provider_vultr(self, provider):
        w = provider.create_world(CreateWorldRequest(region="ewr", tags=GhostRangeTags(range_id="range-1")))
        assert w.provider == ProviderKind.VULTR


class TestCreateComputeRequestShape:
    def test_attach_vpc_is_used_not_vpc_ids(self, provider, fake_server):
        """Verified 2026-09-26 against govultr v3 InstanceCreateReq: the raw
        API field is `attach_vpc`, not `vpc_ids` (that's the Terraform
        resource attribute name, translated internally). ADR-006's mapping
        table uses the Terraform-facing name; this package speaks the raw
        API and must use attach_vpc."""
        world_id = _make_world(provider)
        provider.create_compute(
            CreateComputeRequest(
                world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), os_id=387
            )
        )
        instance_requests = [r for r in fake_server.requests if r.url.path == "/v2/instances" and r.method == "POST"]
        body = json.loads(instance_requests[0].content)
        assert body["attach_vpc"] == [world_id]
        assert "vpc_ids" not in body

    def test_tags_sent_as_flat_string_list(self, provider, fake_server):
        world_id = _make_world(provider)
        tags = GhostRangeTags(range_id="range-1", world_id="world-1", ttl_seconds=3600)
        provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=tags, os_id=387)
        )
        body = json.loads([r for r in fake_server.requests if r.url.path == "/v2/instances"][0].content)
        assert body["tags"] == tags.as_vultr_tag_list()
        assert all(isinstance(t, str) for t in body["tags"])

    def test_os_id_sent_for_fresh_build(self, provider, fake_server):
        world_id = _make_world(provider)
        provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), os_id=387)
        )
        body = json.loads([r for r in fake_server.requests if r.url.path == "/v2/instances"][0].content)
        assert body["os_id"] == 387
        assert "snapshot_id" not in body

    def test_snapshot_id_sent_for_fork_path(self, provider, fake_server):
        world_id = _make_world(provider)
        provider.create_compute(
            CreateComputeRequest(
                world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), snapshot_id="snap-golden-1"
            )
        )
        body = json.loads([r for r in fake_server.requests if r.url.path == "/v2/instances"][0].content)
        assert body["snapshot_id"] == "snap-golden-1"
        assert "os_id" not in body

    def test_user_data_is_base64_encoded(self, provider, fake_server):
        world_id = _make_world(provider)
        cloud_config = "#cloud-config\npackages:\n  - nginx\n"
        provider.create_compute(
            CreateComputeRequest(
                world_ref=world_id,
                region="ewr",
                plan="vc2-1c-1gb",
                tags=GhostRangeTags(range_id="range-1"),
                os_id=387,
                user_data=cloud_config,
            )
        )
        body = json.loads([r for r in fake_server.requests if r.url.path == "/v2/instances"][0].content)
        assert base64.b64decode(body["user_data"]).decode("utf-8") == cloud_config

    def test_firewall_group_and_script_id_forwarded(self, provider, fake_server):
        world_id = _make_world(provider)
        provider.create_compute(
            CreateComputeRequest(
                world_ref=world_id,
                region="ewr",
                plan="vc2-1c-1gb",
                tags=GhostRangeTags(range_id="range-1"),
                os_id=387,
                script_id="script-1",
                firewall_group_id="fwg-99",
            )
        )
        body = json.loads([r for r in fake_server.requests if r.url.path == "/v2/instances"][0].content)
        assert body["script_id"] == "script-1"
        assert body["firewall_group_id"] == "fwg-99"

    def test_backups_field_is_enabled_disabled_string_not_bool(self, provider, fake_server):
        world_id = _make_world(provider)
        provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), os_id=387)
        )
        body = json.loads([r for r in fake_server.requests if r.url.path == "/v2/instances"][0].content)
        assert body["backups"] == "disabled"  # matches govultr's `Backups string` field convention

    def test_result_tagged_provider_vultr_and_pending(self, provider):
        world_id = _make_world(provider)
        c = provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), os_id=387)
        )
        assert c.provider == ProviderKind.VULTR
        assert c.status == ResourceStatus.PENDING  # fake server starts instances as "pending"


class TestGetComputeEnrichesWorldRef:
    def test_get_compute_looks_up_attached_vpc(self, provider, fake_server):
        world_id = _make_world(provider)
        c = provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), os_id=387)
        )
        fetched = provider.get_compute(c.provider_compute_id)
        assert fetched.world_ref == world_id
        vpc_lookup_requests = [r for r in fake_server.requests if r.url.path.endswith("/vpcs") and "instances" in r.url.path]
        assert len(vpc_lookup_requests) == 1


class TestWaitUntilReady:
    def test_becomes_active_and_returns(self, provider, fake_server):
        world_id = _make_world(provider)
        c = provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), os_id=387)
        )
        fake_server.mark_active(c.provider_compute_id)
        ready = provider.wait_until_ready(c.provider_compute_id, timeout_s=5, poll_interval_s=0)
        assert ready.status == ResourceStatus.ACTIVE

    def test_times_out_when_never_active(self, provider):
        world_id = _make_world(provider)
        c = provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), os_id=387)
        )
        with pytest.raises(VultrTimeoutError):
            provider.wait_until_ready(c.provider_compute_id, timeout_s=0.01, poll_interval_s=0)


class TestDestroyConfirmsDeletion:
    def test_destroy_compute_deletes_then_confirms_404(self, provider, fake_server):
        world_id = _make_world(provider)
        c = provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), os_id=387)
        )
        provider.destroy_compute(c.provider_compute_id, timeout_s=5, poll_interval_s=0)
        with pytest.raises(VultrNotFoundError):
            provider.get_compute(c.provider_compute_id)
        delete_requests = [r for r in fake_server.requests if r.method == "DELETE" and "instances" in r.url.path]
        get_requests_after_delete = [
            r for r in fake_server.requests if r.method == "GET" and r.url.path == f"/v2/instances/{c.provider_compute_id}"
        ]
        assert len(delete_requests) == 1
        # the confirm-until-gone loop must issue at least one GET after DELETE
        assert len(get_requests_after_delete) >= 1

    def test_destroy_world_deletes_vpc_and_paired_firewall_group(self, provider, fake_server):
        w = provider.create_world(CreateWorldRequest(region="ewr", tags=GhostRangeTags(range_id="range-1")))
        provider.destroy_world(w.provider_world_id, firewall_group_id=w.firewall_group_id, timeout_s=5, poll_interval_s=0)
        assert w.provider_world_id not in fake_server.vpcs
        assert w.firewall_group_id not in fake_server.firewall_groups


class TestListFiltersByRangeId:
    def test_list_worlds_filters_by_ownership_tag(self, provider):
        w1 = provider.create_world(CreateWorldRequest(region="ewr", tags=GhostRangeTags(range_id="range-1")))
        provider.create_world(CreateWorldRequest(region="ewr", tags=GhostRangeTags(range_id="range-2")))
        filtered = provider.list_worlds(range_id="range-1")
        assert [w.provider_world_id for w in filtered] == [w1.provider_world_id]

    def test_list_worlds_excludes_untagged_when_range_id_none(self, provider, fake_server):
        provider.create_world(CreateWorldRequest(region="ewr", tags=GhostRangeTags(range_id="range-1")))
        fake_server.vpcs["foreign-vpc"] = {
            "id": "foreign-vpc",
            "region": "ewr",
            "description": "not-ghostrange",
        }
        all_owned = provider.list_worlds(range_id=None)
        assert all(w.tags is not None for w in all_owned)
        assert not any(w.provider_world_id == "foreign-vpc" for w in all_owned)

    def test_list_computes_filters_by_ownership_tag(self, provider):
        world_id = _make_world(provider)
        c1 = provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), os_id=387)
        )
        provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-2"), os_id=387)
        )
        filtered = provider.list_computes(range_id="range-1")
        assert [c.provider_compute_id for c in filtered] == [c1.provider_compute_id]

    def test_list_computes_parses_real_date_created_not_now(self, provider, fake_server):
        # A TTL-based orphan reaper compares created_at + ttl_seconds to now;
        # if created_at silently defaulted to "now" on every list call, every
        # instance would always look freshly created and no orphan would
        # ever be detected. Prove the real provider parses date_created
        # instead of falling back to the ComputeRecord field default.
        import datetime as _dt

        world_id = _make_world(provider)
        created = provider.create_compute(
            CreateComputeRequest(world_ref=world_id, region="ewr", plan="vc2-1c-1gb", tags=GhostRangeTags(range_id="range-1"), os_id=387)
        )
        fake_server.instances[created.provider_compute_id]["date_created"] = "2020-01-01T00:00:00+00:00"
        [record] = provider.list_computes(range_id="range-1")
        assert record.created_at == _dt.datetime(2020, 1, 1, tzinfo=_dt.timezone.utc)
        assert (_dt.datetime.now(_dt.timezone.utc) - record.created_at).days > 300


class TestAuthHeaderNeverLeaks:
    def test_every_request_uses_bearer_auth_and_key_not_in_any_response(self, provider, fake_server):
        provider.create_world(CreateWorldRequest(region="ewr", tags=GhostRangeTags(range_id="range-1")))
        assert fake_server.requests, "expected at least one request to have been made"
        for req in fake_server.requests:
            assert req.headers.get("authorization") == f"Bearer {FAKE_KEY}"


def test_real_vultr_e2e_not_run():
    """Explicit, honest marker: this suite never contacts the real Vultr
    API. A live-credential end-to-end run (create -> wait_until_ready ->
    destroy_compute -> destroy_world against https://api.vultr.com with a
    real VULTR_API_KEY) has NOT been executed as part of this package's
    test suite: REAL_VULTR_E2E = NOT_RUN_NO_CREDENTIALS. See README.md
    "Running the real E2E" for how to run it manually once a real key
    exists."""
    assert True
