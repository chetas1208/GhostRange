"""Hard safety boundaries — outside LLM control."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from ghostrange_contracts.adversarial_m8 import SearchCandidateV1

_PRIVATE_NETS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
)

_BLOCKED_HOST_PATTERNS = (
    re.compile(r"metadata\.google", re.I),
    re.compile(r"169\.254\.169\.254"),
)

_EXTERNAL_LITERAL = re.compile(r"^https?://", re.I)


class SearchSafetyError(ValueError):
    pass


def assert_candidate_in_range(
    candidate: SearchCandidateV1,
    *,
    authorized_asset_ids: set[str],
    max_sequence_length: int,
    max_payload_bytes: int = 65536,
) -> None:
    if candidate.world_asset_id not in authorized_asset_ids:
        raise SearchSafetyError(f"asset {candidate.world_asset_id!r} not authorized")

    if len(candidate.action_sequence) > max_sequence_length:
        raise SearchSafetyError("action sequence exceeds max_sequence_length")

    for step in candidate.action_sequence:
        _validate_action_step(step, authorized_asset_ids, max_payload_bytes)


def _validate_action_step(step: dict, authorized_asset_ids: set[str], max_payload_bytes: int) -> None:
    target = step.get("target_asset_id") or step.get("world_asset_id")
    if target and target not in authorized_asset_ids:
        raise SearchSafetyError(f"step targets unauthorized asset {target!r}")

    host = step.get("host") or step.get("hostname")
    if host:
        _reject_external_host(str(host))

    url = step.get("url")
    if url:
        parsed = urlparse(str(url))
        if parsed.hostname:
            _reject_external_host(parsed.hostname)

    body = step.get("body")
    if isinstance(body, (str, bytes)) and len(body) > max_payload_bytes:
        raise SearchSafetyError("payload too large")

    if step.get("credential_ref") and not str(step["credential_ref"]).startswith("range-synthetic/"):
        raise SearchSafetyError("only range-synthetic credentials allowed")


def _reject_external_host(host: str) -> None:
    for pat in _BLOCKED_HOST_PATTERNS:
        if pat.search(host):
            raise SearchSafetyError(f"blocked host pattern: {host}")
    if host in ("localhost", "127.0.0.1"):
        return
    try:
        ip = ipaddress.ip_address(host)
        if not any(ip in net for net in _PRIVATE_NETS):
            raise SearchSafetyError(f"host {host} outside private range allowlist")
    except ValueError:
        if _EXTERNAL_LITERAL.match(host):
            raise SearchSafetyError("raw external URL host not allowed")
        if "." in host and not host.endswith(".ghostrange.local"):
            raise SearchSafetyError(f"unscoped hostname {host!r}")


__all__ = ["assert_candidate_in_range", "SearchSafetyError"]
