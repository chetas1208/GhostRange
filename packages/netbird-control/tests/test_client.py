"""Tests for NetBirdClient's high-level operations (peer lookup, readiness
check, revocation, groups, setup-key creation) against FakeNetBirdServer —
no real NetBird account touched.
"""

from __future__ import annotations

import httpx
import pytest

from ghostrange_netbird_control import NetBirdClient
from ghostrange_netbird_control.http_client import NetBirdHTTPClient

from fake_netbird_server import FAKE_TOKEN, FakeNetBirdServer


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    monkeypatch.setattr("ghostrange_netbird_control.http_client.time.sleep", lambda _s: None)


def make_client(server: FakeNetBirdServer) -> NetBirdClient:
    http = NetBirdHTTPClient(api_token=FAKE_TOKEN, transport=httpx.MockTransport(server.handler))
    return NetBirdClient(http=http)


class TestFindPeer:
    def test_find_peer_by_name_matches(self):
        server = FakeNetBirdServer()
        server.add_peer(name="gr-worker-ab12cd34", connected=True, group_names=["ghostrange-workers"])
        client = make_client(server)

        peer = client.find_peer_by_name("gr-worker-ab12cd34")
        assert peer is not None
        assert peer.connected is True
        assert "ghostrange-workers" in peer.group_names

    def test_find_peer_by_hostname_fallback(self):
        server = FakeNetBirdServer()
        server.add_peer(name="different-display-name", hostname="gr-worker-zz99", connected=True)
        client = make_client(server)

        peer = client.find_peer_by_name("gr-worker-zz99")
        assert peer is not None

    def test_find_peer_returns_none_when_absent(self):
        server = FakeNetBirdServer()
        client = make_client(server)

        assert client.find_peer_by_name("gr-worker-never-enrolled") is None


class TestIsPeerReady:
    def test_ready_when_connected_and_in_group(self):
        server = FakeNetBirdServer()
        server.add_peer(name="w1", connected=True, group_names=["ghostrange-workers"])
        client = make_client(server)
        peer = client.find_peer_by_name("w1")

        assert client.is_peer_ready(peer, group="ghostrange-workers") is True

    def test_not_ready_when_connected_but_wrong_group(self):
        server = FakeNetBirdServer()
        server.add_peer(name="w1", connected=True, group_names=["some-other-group"])
        client = make_client(server)
        peer = client.find_peer_by_name("w1")

        assert client.is_peer_ready(peer, group="ghostrange-workers") is False

    def test_not_ready_when_in_group_but_not_connected(self):
        server = FakeNetBirdServer()
        server.add_peer(name="w1", connected=False, group_names=["ghostrange-workers"])
        client = make_client(server)
        peer = client.find_peer_by_name("w1")

        assert client.is_peer_ready(peer, group="ghostrange-workers") is False

    def test_not_ready_when_neither(self):
        server = FakeNetBirdServer()
        server.add_peer(name="w1", connected=False, group_names=[])
        client = make_client(server)
        peer = client.find_peer_by_name("w1")

        assert client.is_peer_ready(peer, group="ghostrange-workers") is False

    def test_becomes_ready_after_polling_state_change(self):
        """Simulates the readiness gate's poll loop: peer starts
        disconnected/ungrouped, then transitions to connected+grouped
        (as would happen once `netbird up` completes on the real VM)."""
        server = FakeNetBirdServer()
        peer_record = server.add_peer(name="w1", connected=False)
        client = make_client(server)

        assert client.is_peer_ready(client.find_peer_by_name("w1"), group="ghostrange-workers") is False

        server.set_peer_connected(peer_record["id"], True)
        server.add_peer_to_group(peer_record["id"], "ghostrange-workers")

        assert client.is_peer_ready(client.find_peer_by_name("w1"), group="ghostrange-workers") is True


class TestRevokePeer:
    def test_revoke_peer_by_name_removes_it(self):
        server = FakeNetBirdServer()
        server.add_peer(name="w1", connected=True)
        client = make_client(server)

        assert client.revoke_peer_by_name("w1") is True
        assert client.find_peer_by_name("w1") is None

    def test_revoke_peer_by_name_absent_is_noop_false(self):
        server = FakeNetBirdServer()
        client = make_client(server)

        assert client.revoke_peer_by_name("never-existed") is False

    def test_revoke_peer_is_idempotent_on_already_gone_peer(self):
        server = FakeNetBirdServer()
        peer = server.add_peer(name="w1")
        client = make_client(server)

        client.revoke_peer(peer["id"])
        # Second revoke of the same (now-404) id must not raise.
        client.revoke_peer(peer["id"])


class TestGroups:
    def test_list_groups(self):
        server = FakeNetBirdServer()
        server.add_group(name="ghostrange-workers")
        server.add_group(name="ghostrange-control")
        client = make_client(server)

        names = {g.name for g in client.list_groups()}
        assert names == {"ghostrange-workers", "ghostrange-control"}

    def test_find_group_by_name(self):
        server = FakeNetBirdServer()
        server.add_group(name="ghostrange-workers")
        client = make_client(server)

        group = client.find_group_by_name("ghostrange-workers")
        assert group is not None
        assert group.name == "ghostrange-workers"

    def test_find_group_by_name_absent(self):
        server = FakeNetBirdServer()
        client = make_client(server)

        assert client.find_group_by_name("nope") is None


class TestSetupKeys:
    def test_create_setup_key_returns_plaintext_key(self):
        server = FakeNetBirdServer()
        group = server.add_group(name="ghostrange-workers")
        client = make_client(server)

        key = client.create_setup_key(name="worker-abc", auto_group_ids=[group["id"]])
        assert key.key  # plaintext key present on create response
        assert key.auto_groups == [group["id"]]
