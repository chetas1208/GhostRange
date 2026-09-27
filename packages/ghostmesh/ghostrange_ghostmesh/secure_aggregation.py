"""Agent 11 — pedagogical secure sum (mask cancel in cohort); not production crypto."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass


@dataclass
class MaskedShare:
    node_id: str
    masked_value: float


def _mask(node_id: str, round_id: str) -> float:
    h = hashlib.sha256(f"{node_id}:{round_id}".encode()).hexdigest()
    rng = random.Random(int(h[:16], 16))
    return rng.uniform(-1000, 1000)


def secure_sum(values: dict[str, float], *, round_id: str) -> float:
    """Pairwise masks cancel when all participants submit; coordinator sees sum only."""
    if not values:
        return 0.0
    total = sum(values.values())
    mask_sum = sum(_mask(nid, round_id) for nid in values)
    # Each node would send value + mask; here we simulate cancellation
    unmask = sum(_mask(nid, round_id) for nid in values)
    return total + mask_sum - unmask
