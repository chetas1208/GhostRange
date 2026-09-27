"""Deterministic digests for promotion candidates."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ghostrange_contracts.ghostgate_m11 import ProductionChangeCandidateV1


def candidate_payload_for_hash(candidate: ProductionChangeCandidateV1) -> dict[str, Any]:
    data = candidate.model_dump(mode="json")
    for key in ("change_candidate_hash", "state", "created_at", "id"):
        data.pop(key, None)
    return data


def digest_candidate(candidate: ProductionChangeCandidateV1) -> str:
    payload = json.dumps(candidate_payload_for_hash(candidate), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
