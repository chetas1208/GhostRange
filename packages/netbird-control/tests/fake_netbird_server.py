"""A minimal in-memory fake of the NetBird management API, exposed as an
``httpx.MockTransport`` handler. Used by this package's own tests and
importable by ``apps/api``'s tests so the worker readiness gate and
teardown-revocation hook can be tested without ever calling the real
NetBird API.

Deliberately tiny: only the endpoints ``NetBirdClient`` actually calls.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

FAKE_TOKEN = "nbtok-test-not-a-real-netbird-token-0000"


class FakeNetBirdServer:
    def __init__(self) -> None:
        self.peers: dict[str, dict[str, Any]] = {}
        self.groups: dict[str, dict[str, Any]] = {}
        self.setup_keys: dict[str, dict[str, Any]] = {}
        self.requests: list[httpx.Request] = []

    # -- fixtures / setup helpers ----------------------------------------

    def add_group(self, *, name: str, group_id: str | None = None) -> dict[str, Any]:
        gid = group_id or f"grp-{uuid.uuid4().hex[:8]}"
        group = {"id": gid, "name": name, "peers_count": 0}
        self.groups[gid] = group
        return group

    def add_peer(
        self,
        *,
        name: str,
        connected: bool = False,
        group_names: list[str] | None = None,
        peer_id: str | None = None,
        hostname: str | None = None,
    ) -> dict[str, Any]:
        pid = peer_id or f"peer-{uuid.uuid4().hex[:8]}"
        groups = []
        for gname in group_names or []:
            existing = next((g for g in self.groups.values() if g["name"] == gname), None)
            if existing is None:
                existing = self.add_group(name=gname)
            groups.append({"id": existing["id"], "name": existing["name"]})
        peer = {
            "id": pid,
            "name": name,
            "hostname": hostname or name,
            "ip": "100.64.0.1",
            "connected": connected,
            "last_seen": "2026-09-27T00:00:00Z",
            "groups": groups,
            "ssh_enabled": False,
        }
        self.peers[pid] = peer
        return peer

    def set_peer_connected(self, peer_id: str, connected: bool) -> None:
        self.peers[peer_id]["connected"] = connected

    def add_peer_to_group(self, peer_id: str, group_name: str) -> None:
        group = next((g for g in self.groups.values() if g["name"] == group_name), None)
        if group is None:
            group = self.add_group(name=group_name)
        peer = self.peers[peer_id]
        if not any(g["id"] == group["id"] for g in peer["groups"]):
            peer["groups"].append({"id": group["id"], "name": group["name"]})

    # -- transport handler -------------------------------------------------

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Token "):
            return httpx.Response(401, json={"message": "missing token"})

        method, path = request.method, request.url.path

        if method == "GET" and path == "/api/peers":
            return httpx.Response(200, json=list(self.peers.values()))
        if method == "GET" and path.startswith("/api/peers/"):
            pid = path.rsplit("/", 1)[-1]
            if pid not in self.peers:
                return httpx.Response(404, json={"message": "peer not found"})
            return httpx.Response(200, json=self.peers[pid])
        if method == "DELETE" and path.startswith("/api/peers/"):
            pid = path.rsplit("/", 1)[-1]
            if pid not in self.peers:
                return httpx.Response(404, json={"message": "peer not found"})
            del self.peers[pid]
            return httpx.Response(204)
        if method == "GET" and path == "/api/groups":
            return httpx.Response(200, json=list(self.groups.values()))
        if method == "POST" and path == "/api/setup-keys":
            body = json.loads(request.content or b"{}")
            kid = f"key-{uuid.uuid4().hex[:8]}"
            key = {
                "id": kid,
                "key": f"setup-key-{uuid.uuid4().hex}",
                "name": body.get("name", ""),
                "type": body.get("type", "reusable"),
                "expires_at": None,
                "auto_groups": body.get("auto_groups", []),
            }
            self.setup_keys[kid] = key
            return httpx.Response(201, json=key)

        return httpx.Response(404, json={"message": f"unhandled {method} {path}"})


__all__ = ["FakeNetBirdServer", "FAKE_TOKEN"]
