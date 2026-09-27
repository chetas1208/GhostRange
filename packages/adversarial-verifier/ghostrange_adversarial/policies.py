from __future__ import annotations

import random
from typing import Iterable

from ghostrange_contracts.adversarial_m8 import SearchArmKind, SearchArmV1, SearchPolicyId


def select_arm(
    policy: SearchPolicyId,
    arms: list[SearchArmV1],
    *,
    rng: random.Random,
    round_robin_index: list[int],
) -> SearchArmKind:
    enabled = [a for a in arms if a.priority_weight > 0]
    if not enabled:
        return arms[0].kind

    if policy == SearchPolicyId.UNIFORM_RANDOM:
        return rng.choice(enabled).kind
    if policy == SearchPolicyId.ROUND_ROBIN:
        idx = round_robin_index[0] % len(enabled)
        round_robin_index[0] += 1
        return enabled[idx].kind
    if policy == SearchPolicyId.STATIC_PRIORITY:
        return max(enabled, key=lambda a: a.priority_weight).kind
    if policy == SearchPolicyId.NOVELTY_GREEDY:
        return max(enabled, key=lambda a: (a.novel_observations, -a.attempts)).kind
    # GHOSTSCHEDULER_SEARCH — cost-adjusted value
    return max(enabled, key=lambda a: _arm_value(a)).kind


def _arm_value(arm: SearchArmV1) -> float:
    if arm.attempts == 0:
        return arm.priority_weight * 2.0
    rate = arm.novel_observations / max(1, arm.attempts)
    ce_rate = arm.counterexamples / max(1, arm.attempts)
    return rate * 3.0 + ce_rate * 10.0 + arm.priority_weight * 0.1


def iter_candidates_for_arm(candidates: list, arm: SearchArmKind) -> Iterable:
    return (c for c in candidates if c.arm == arm)


__all__ = ["select_arm"]
