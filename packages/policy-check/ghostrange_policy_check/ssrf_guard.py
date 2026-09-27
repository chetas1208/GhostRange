"""Concrete SSRF backstop for the B7 trust boundary (THREAT_MODEL.md T6):
"any control-plane HTTP-issuing code ⇄ cloud metadata / arbitrary internal
hosts."

The primary control is architectural (T6's real mitigation): no tool
exposed to the LLM agent accepts an arbitrary URL, and vultr-control's
calls to the real Vultr API use a fixed, config-sourced base URL, never one
derived from agent/range output. This module is the defense-in-depth layer
underneath that: for the one legitimate case where control-plane code MUST
resolve a caller-influenced host (range-runtime's mediated evidence-fetch
proxy reaching into a range network), every such call must pass through
``assert_safe_egress_url``/``resolve_and_check`` first. Fail-closed
throughout: unparseable, unresolvable, or ambiguous input is rejected, not
passed through "to be safe."

Blocks, in both IPv4 and IPv6: loopback, RFC1918/ULA private ranges, and
link-local — the last of which is deliberate and important: Vultr's own
cloud metadata endpoint (169.254.169.254, confirmed in
docs/research/VULTR.md §4) lives in link-local space, as does every other
major cloud's metadata service. A single "block link-local" rule closes
the metadata-SSRF path without needing to special-case one IP literal.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

VULTR_METADATA_HOST = "169.254.169.254"

_BLOCKED_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",  # link-local -- covers the Vultr/AWS/GCP/Azure metadata IP
        "0.0.0.0/8",
        "::1/128",
        "fc00::/7",  # unique local
        "fe80::/10",  # link-local
    )
)


class SSRFBlockedError(Exception):
    """Raised whenever a host/URL this module is asked to check resolves
    (or fails to resolve cleanly) into disallowed space. Always fail
    closed: the caller must treat this exactly like a policy DENY — no
    retry with a "just this once" bypass.
    """


def is_blocked_address(ip: str) -> bool:
    """True if ``ip`` is loopback/private/link-local (includes the cloud
    metadata endpoint) — or if it isn't a parseable IP at all, since an
    unparseable value must never be treated as "probably fine."
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return any(addr in network for network in _BLOCKED_NETWORKS)


def resolve_and_check(host: str) -> str:
    """Resolve ``host`` and raise ``SSRFBlockedError`` if ANY resolved
    address is blocked, or if resolution itself fails. Returns the first
    resolved address on success purely for caller convenience/logging.
    """
    try:
        addrinfo = socket.getaddrinfo(host, None)
    except OSError as exc:
        raise SSRFBlockedError(f"could not resolve {host!r}: {exc}") from exc
    if not addrinfo:
        raise SSRFBlockedError(f"{host!r} resolved to no addresses")
    resolved_ips = [info[4][0] for info in addrinfo]
    for ip in resolved_ips:
        if is_blocked_address(ip):
            raise SSRFBlockedError(f"{host!r} resolves to blocked address {ip}")
    return resolved_ips[0]


def assert_safe_egress_url(url: str, *, allowed_hosts: frozenset[str] | None = None) -> None:
    """The mandatory pre-flight check before any HTTP call whose host came
    from agent output, range output, or any other value this process did
    not fully control end-to-end. Never call requests/httpx directly on
    such input without first calling this.

    ``allowed_hosts``, when given, makes this an allowlist check (the
    stronger property T6 actually wants for the mediated evidence-fetch
    proxy: not just "not obviously internal" but "is the one specific
    pre-registered per-range endpoint"). Prefer passing it whenever the
    caller has a known-good host set instead of relying on the denylist
    alone.
    """
    parsed = urlparse(url if "://" in url else f"//{url}", scheme="https")
    host = parsed.hostname
    if not host:
        raise SSRFBlockedError(f"could not extract a host from {url!r}")
    if allowed_hosts is not None and host not in allowed_hosts:
        raise SSRFBlockedError(f"{host!r} is not in the caller's allowed_hosts allowlist")
    resolve_and_check(host)


__all__ = [
    "VULTR_METADATA_HOST",
    "SSRFBlockedError",
    "is_blocked_address",
    "resolve_and_check",
    "assert_safe_egress_url",
]
