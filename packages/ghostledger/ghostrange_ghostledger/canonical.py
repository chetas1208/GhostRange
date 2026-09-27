"""Deterministic JSON canonicalization (RFC 8785-inspired subset)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _sort_keys(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sort_keys(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_sort_keys(x) for x in obj]
    return obj


def canonical_json_bytes(model_or_dict: Any) -> bytes:
    if hasattr(model_or_dict, "model_dump"):
        data = model_or_dict.model_dump(mode="json")
    else:
        data = model_or_dict
    ordered = _sort_keys(data)
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_sha256(model_or_dict: Any) -> str:
    h = hashlib.sha256(canonical_json_bytes(model_or_dict)).hexdigest()
    return f"sha256:{h}"


__all__ = ["canonical_json_bytes", "digest_sha256"]
