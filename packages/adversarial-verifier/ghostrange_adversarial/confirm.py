from __future__ import annotations

from typing import Any, Callable

from ghostrange_contracts.adversarial_m8 import CounterexampleReproducibility


def confirm_counterexample(
    action_sequence: list[dict[str, Any]],
    *,
    execute_fresh_world: Callable[[list[dict[str, Any]]], dict[str, Any]],
    oracle_satisfied: Callable[[dict[str, Any]], bool],
    runs: int,
    world_healthy: Callable[[], bool] | None = None,
) -> CounterexampleReproducibility:
    if world_healthy and not world_healthy():
        return CounterexampleReproducibility.REJECTED_FALSE_POSITIVE

    successes = 0
    for _ in range(runs):
        obs = execute_fresh_world(action_sequence)
        if oracle_satisfied(obs):
            successes += 1
    if successes == runs:
        return CounterexampleReproducibility.CONFIRMED
    if successes == 0:
        return CounterexampleReproducibility.REJECTED_FALSE_POSITIVE
    return CounterexampleReproducibility.UNCONFIRMED


__all__ = ["confirm_counterexample"]
