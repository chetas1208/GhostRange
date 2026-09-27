"""Tests for ghostrange_api.netbird_gate: the NetBird mesh-enrollment
readiness gate.

Two things this suite must prove:

1. Inertness (NETBIRD_ENABLED=false, the current default): the gate makes
   no NetBird API call, never touches the worker store, and returns
   immediately — behavior identical to before NetBird existed.
2. When enabled: a worker isn't "ready" until its NetBird peer is both
   connected AND in the required group; a peer that never reaches that
   state within the timeout gets BOOTSTRAP_FAILED recorded and
   NetBirdBootstrapFailed raised.

All against ghostrange_netbird_control's FakeNetBirdServer — no real
NetBird account touched, no Postgres required (a minimal fake WorkerStore
stands in for the real one; the gate only ever calls
``mark_worker_bootstrap_failed`` on it).
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from ghostrange_api.config import Settings
from ghostrange_api.netbird_gate import (
    NetBirdBootstrapFailed,
    build_netbird_client,
    ensure_worker_mesh_ready,
    revoke_worker_peer,
)
from ghostrange_netbird_control import NetBirdClient
from ghostrange_netbird_control.http_client import NetBirdHTTPClient

import sys
from pathlib import Path

# FakeNetBirdServer lives in the netbird-control package's own tests/ dir
# (mirrors packages/vultr-control's fake_vultr_server.py convention) — it's
# not part of the installed package, so import it by path.
_NETBIRD_TESTS_DIR = Path(__file__).resolve().parents[3] / "packages" / "netbird-control" / "tests"
sys.path.insert(0, str(_NETBIRD_TESTS_DIR))
from fake_netbird_server import FAKE_TOKEN, FakeNetBirdServer  # noqa: E402

_ENV_KEYS = (
    "NETBIRD_ENABLED",
    "NETBIRD_API_TOKEN",
    "NETBIRD_WORKER_SETUP_KEY",
    "NETBIRD_WORKER_GROUP",
    "NETBIRD_ENROLL_TIMEOUT_S",
)


def _settings(monkeypatch, **env_overrides) -> Settings:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, str(value))
    return Settings.from_env()


class FakeWorkerStore:
    """Duck-typed stand-in for WorkerStore — the gate only ever calls
    mark_worker_bootstrap_failed on it. No Postgres needed."""

    def __init__(self) -> None:
        self.bootstrap_failed_calls: list[tuple[uuid.UUID, str]] = []

    async def mark_worker_bootstrap_failed(self, worker_id: uuid.UUID, *, reason: str) -> None:
        self.bootstrap_failed_calls.append((worker_id, reason))


def make_client(server: FakeNetBirdServer) -> NetBirdClient:
    http = NetBirdHTTPClient(api_token=FAKE_TOKEN, transport=httpx.MockTransport(server.handler))
    return NetBirdClient(http=http)


class TestInertness:
    """NETBIRD_ENABLED=false must make this feature a complete no-op."""

    def test_disabled_by_default(self, monkeypatch):
        settings = _settings(monkeypatch)
        assert settings.netbird_enabled is False

    def test_build_netbird_client_returns_none_when_disabled(self, monkeypatch):
        settings = _settings(monkeypatch, NETBIRD_ENABLED="false", NETBIRD_API_TOKEN="whatever")
        assert build_netbird_client(settings) is None

    async def test_ensure_worker_mesh_ready_returns_immediately_when_disabled(self, monkeypatch):
        settings = _settings(monkeypatch, NETBIRD_ENABLED="false")
        store = FakeWorkerStore()
        worker_id = uuid.uuid4()

        # client=None and a nonsense peer name: if the gate did anything
        # other than return immediately, this would raise (None has no
        # find_peer_by_name) or hang polling forever.
        await ensure_worker_mesh_ready(
            settings=settings,
            store=store,
            client=None,
            worker_id=worker_id,
            peer_hostname="does-not-matter",
            timeout_s=0.01,
        )
        assert store.bootstrap_failed_calls == []

    def test_revoke_worker_peer_is_noop_when_disabled(self, monkeypatch):
        settings = _settings(monkeypatch, NETBIRD_ENABLED="false")
        # client=None: if this weren't a no-op it would raise (None.revoke_peer_by_name).
        revoke_worker_peer(settings, None, "some-worker-hostname")

    def test_revoke_worker_peer_is_noop_with_none_client_even_if_flag_set(self, monkeypatch):
        settings = _settings(monkeypatch, NETBIRD_ENABLED="true", NETBIRD_API_TOKEN="x")
        revoke_worker_peer(settings, None, "some-worker-hostname")


class TestMisconfiguration:
    def test_build_netbird_client_raises_when_enabled_without_token(self, monkeypatch):
        settings = _settings(monkeypatch, NETBIRD_ENABLED="true")
        with pytest.raises(RuntimeError, match="NETBIRD_API_TOKEN"):
            build_netbird_client(settings)

    async def test_ensure_worker_mesh_ready_raises_when_enabled_without_client(self, monkeypatch):
        settings = _settings(monkeypatch, NETBIRD_ENABLED="true", NETBIRD_API_TOKEN="x")
        store = FakeWorkerStore()
        with pytest.raises(RuntimeError, match="no NetBirdClient"):
            await ensure_worker_mesh_ready(
                settings=settings,
                store=store,
                client=None,
                worker_id=uuid.uuid4(),
                peer_hostname="gr-worker-abc",
                timeout_s=0.01,
            )


class TestReadinessGateEnabled:
    async def test_ready_immediately_when_peer_already_connected_and_grouped(self, monkeypatch):
        settings = _settings(
            monkeypatch, NETBIRD_ENABLED="true", NETBIRD_API_TOKEN="x", NETBIRD_WORKER_GROUP="ghostrange-workers"
        )
        server = FakeNetBirdServer()
        server.add_peer(name="gr-worker-abc12345", connected=True, group_names=["ghostrange-workers"])
        client = make_client(server)
        store = FakeWorkerStore()

        await ensure_worker_mesh_ready(
            settings=settings,
            store=store,
            client=client,
            worker_id=uuid.uuid4(),
            peer_hostname="gr-worker-abc12345",
            timeout_s=1.0,
            poll_s=0.01,
        )
        assert store.bootstrap_failed_calls == []

    async def test_becomes_ready_after_a_few_polls(self, monkeypatch):
        """Peer enrolls (connects + joins group) partway through the poll
        loop — simulates real `netbird up` timing on the VM."""
        settings = _settings(
            monkeypatch, NETBIRD_ENABLED="true", NETBIRD_API_TOKEN="x", NETBIRD_WORKER_GROUP="ghostrange-workers"
        )
        server = FakeNetBirdServer()
        peer = server.add_peer(name="gr-worker-delayed", connected=False)
        client = make_client(server)
        store = FakeWorkerStore()

        calls = {"n": 0}
        real_find = client.find_peer_by_name

        def flaky_find(name):
            calls["n"] += 1
            if calls["n"] >= 3:
                server.set_peer_connected(peer["id"], True)
                server.add_peer_to_group(peer["id"], "ghostrange-workers")
            return real_find(name)

        monkeypatch.setattr(client, "find_peer_by_name", flaky_find)

        await ensure_worker_mesh_ready(
            settings=settings,
            store=store,
            client=client,
            worker_id=uuid.uuid4(),
            peer_hostname="gr-worker-delayed",
            timeout_s=5.0,
            poll_s=0.01,
        )
        assert calls["n"] >= 3
        assert store.bootstrap_failed_calls == []

    async def test_bootstrap_failed_on_timeout_never_enrolled(self, monkeypatch):
        settings = _settings(
            monkeypatch, NETBIRD_ENABLED="true", NETBIRD_API_TOKEN="x", NETBIRD_WORKER_GROUP="ghostrange-workers"
        )
        server = FakeNetBirdServer()  # no peer ever added — worker never joins the mesh
        client = make_client(server)
        store = FakeWorkerStore()
        worker_id = uuid.uuid4()

        with pytest.raises(NetBirdBootstrapFailed):
            await ensure_worker_mesh_ready(
                settings=settings,
                store=store,
                client=client,
                worker_id=worker_id,
                peer_hostname="gr-worker-ghost",
                timeout_s=0.05,
                poll_s=0.01,
            )
        assert len(store.bootstrap_failed_calls) == 1
        called_worker_id, reason = store.bootstrap_failed_calls[0]
        assert called_worker_id == worker_id
        assert "gr-worker-ghost" in reason

    async def test_bootstrap_failed_on_timeout_connected_but_wrong_group(self, monkeypatch):
        """Peer connects but never lands in the required group (e.g. the
        setup key's auto_groups didn't include it) — must still time out
        and fail, connectivity alone is not readiness."""
        settings = _settings(
            monkeypatch, NETBIRD_ENABLED="true", NETBIRD_API_TOKEN="x", NETBIRD_WORKER_GROUP="ghostrange-workers"
        )
        server = FakeNetBirdServer()
        server.add_peer(name="gr-worker-wrong-group", connected=True, group_names=["some-other-group"])
        client = make_client(server)
        store = FakeWorkerStore()
        worker_id = uuid.uuid4()

        with pytest.raises(NetBirdBootstrapFailed):
            await ensure_worker_mesh_ready(
                settings=settings,
                store=store,
                client=client,
                worker_id=worker_id,
                peer_hostname="gr-worker-wrong-group",
                timeout_s=0.05,
                poll_s=0.01,
            )
        assert len(store.bootstrap_failed_calls) == 1

    def test_revoke_worker_peer_calls_client_when_enabled(self, monkeypatch):
        settings = _settings(monkeypatch, NETBIRD_ENABLED="true", NETBIRD_API_TOKEN="x")
        server = FakeNetBirdServer()
        server.add_peer(name="gr-worker-to-revoke", connected=True)
        client = make_client(server)

        revoke_worker_peer(settings, client, "gr-worker-to-revoke")
        assert client.find_peer_by_name("gr-worker-to-revoke") is None

    def test_revoke_worker_peer_swallows_control_errors(self, monkeypatch):
        """A NetBird-side outage during teardown must not raise out of the
        teardown path — the Vultr VM termination this runs alongside must
        still be able to complete."""
        settings = _settings(monkeypatch, NETBIRD_ENABLED="true", NETBIRD_API_TOKEN="x")

        def broken_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"message": "netbird down"})

        http = NetBirdHTTPClient(api_token=FAKE_TOKEN, transport=httpx.MockTransport(broken_handler), max_retries=0)
        client = NetBirdClient(http=http)

        revoke_worker_peer(settings, client, "gr-worker-doesnt-matter")  # must not raise
