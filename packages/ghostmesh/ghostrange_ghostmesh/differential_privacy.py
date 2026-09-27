"""Agent 10 — DP for aggregate counts only (not arbitrary structured artifacts)."""

from __future__ import annotations

import hashlib
import random

from ghostrange_contracts.ghostmesh_m13 import PrivacyBudgetV1


def laplace_noise(*, sensitivity: float, epsilon: float, seed: str) -> float:
    if epsilon <= 0:
        raise ValueError("epsilon must be positive for DP noise")
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16))
    u = rng.random() - 0.5
    scale = sensitivity / epsilon
    return -scale * (1 if u < 0 else -1) * (1 - 2 * abs(u))


def noisy_count(true_count: int, *, epsilon: float, delta: float, scope: str) -> tuple[int, PrivacyBudgetV1]:
    noise = laplace_noise(sensitivity=1.0, epsilon=epsilon, seed=f"{scope}:{true_count}")
    reported = max(0, int(round(true_count + noise)))
    budget = PrivacyBudgetV1(
        epsilon=epsilon,
        delta=delta,
        mechanism="laplace",
        scope=scope,
        consumed=epsilon,
    )
    return reported, budget
