"""Merkle root over sorted artifact digests (SHA-256)."""

from __future__ import annotations

import hashlib
from typing import Iterable


def _hex_from_digest(d: str) -> bytes:
    if d.startswith("sha256:"):
        d = d[7:]
    return bytes.fromhex(d)


def merkle_root(digests: Iterable[str]) -> str:
    leaves = sorted(_hex_from_digest(d) for d in digests)
    if not leaves:
        empty = hashlib.sha256(b"").hexdigest()
        return f"sha256:{empty}"
    layer = leaves
    while len(layer) > 1:
        nxt: list[bytes] = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            nxt.append(hashlib.sha256(left + right).digest())
        layer = nxt
    return f"sha256:{layer[0].hex()}"


__all__ = ["merkle_root"]
