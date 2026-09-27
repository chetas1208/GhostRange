"""High-level NetBird operations GhostRange actually needs.

Deliberately narrow: this is not a full NetBird API SDK. It covers exactly
what the worker readiness gate and worker teardown path need:

- find a worker's peer (by name/hostname) and check whether it is
  connected + in the right policy group (micro-segmentation gate),
- list groups (diagnostics / the one read-only "does this token work"
  check),
- revoke a peer on worker teardown,
- optionally mint a setup key server-side (not wired into the default
  provisioning path yet).
"""

from __future__ import annotations

from typing import Optional

from .errors import NetBirdNotFoundError
from .http_client import DEFAULT_BASE_URL, NetBirdHTTPClient
from .models import Group, Peer, SetupKey


class NetBirdClient:
    def __init__(
        self,
        api_token: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        http: Optional[NetBirdHTTPClient] = None,
        **http_kwargs,
    ) -> None:
        self._http = http or NetBirdHTTPClient(api_token, base_url=base_url, **http_kwargs)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "NetBirdClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- peers ---------------------------------------------------------

    def list_peers(self) -> list[Peer]:
        data = self._http.request("GET", "/api/peers") or []
        return [Peer.from_api(p) for p in data]

    def get_peer(self, peer_id: str) -> Peer:
        data = self._http.request("GET", f"/api/peers/{peer_id}")
        return Peer.from_api(data)

    def find_peer_by_name(self, name: str) -> Optional[Peer]:
        """Look up a peer by its NetBird ``name`` (falls back to matching
        ``hostname``) — this is how the readiness gate finds "its" peer
        without ever needing NetBird's own peer id, since the peer id is
        only known *after* successful enrollment. Returns ``None`` (never
        raises ``NetBirdNotFoundError``) when no matching peer exists yet —
        "not enrolled yet" is an expected, poll-worthy state, not an error.
        """
        for peer in self.list_peers():
            if peer.name == name or peer.hostname == name:
                return peer
        return None

    def is_peer_ready(self, peer: Peer, *, group: str) -> bool:
        """A peer is "ready" for the micro-segmentation gate once it is
        both connected to the management server AND a member of `group`.
        Connectivity alone is not enough — GhostShield-adjacent policy
        groups only apply once the peer actually landed in the right
        group, e.g. if group auto-assignment from the setup key failed or
        an operator changed the setup key's auto_groups."""
        return bool(peer.connected) and group in peer.group_names

    def revoke_peer(self, peer_id: str) -> None:
        """Delete a peer from the mesh. Idempotent: a peer that is already
        gone (404) is treated as success, not an error — the caller (worker
        teardown) doesn't need to track whether it already revoked this
        peer."""
        try:
            self._http.request("DELETE", f"/api/peers/{peer_id}")
        except NetBirdNotFoundError:
            pass

    def revoke_peer_by_name(self, name: str) -> bool:
        """Convenience for the worker-teardown hook: find-then-revoke by
        name. Returns True if a matching peer was found and revoked, False
        if no matching peer existed (nothing to revoke)."""
        peer = self.find_peer_by_name(name)
        if peer is None:
            return False
        self.revoke_peer(peer.id)
        return True

    # -- groups ----------------------------------------------------------

    def list_groups(self) -> list[Group]:
        data = self._http.request("GET", "/api/groups") or []
        return [Group.from_api(g) for g in data]

    def find_group_by_name(self, name: str) -> Optional[Group]:
        for group in self.list_groups():
            if group.name == name:
                return group
        return None

    # -- setup keys --------------------------------------------------------

    def create_setup_key(
        self,
        *,
        name: str,
        auto_group_ids: list[str],
        setup_key_type: str = "one-off",
        expires_in_s: int = 3600,
    ) -> SetupKey:
        """Mint a fresh setup key server-side, auto-assigned to
        `auto_group_ids` (e.g. the ``ghostrange-workers`` group's id).
        Not called anywhere in the default provisioning path today — the
        static ``NETBIRD_WORKER_SETUP_KEY`` covers current needs — but
        available for a future upgrade to per-worker ephemeral keys
        without needing a new client method. This is a MUTATING call:
        never invoke it against a real account from a test.
        """
        body = {
            "name": name,
            "type": setup_key_type,
            "expires_in": expires_in_s,
            "auto_groups": auto_group_ids,
            "usage_limit": 1 if setup_key_type == "one-off" else 0,
        }
        data = self._http.request("POST", "/api/setup-keys", json_body=body)
        return SetupKey.from_api(data)


__all__ = ["NetBirdClient"]
