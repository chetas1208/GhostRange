"""Delta-style local minimization of action sequences."""

from __future__ import annotations

from typing import Any, Callable

from ghostrange_contracts.adversarial_m8 import MinimalityLevel


def minimize_sequence(
    sequence: list[dict[str, Any]],
    *,
    still_falsifies: Callable[[list[dict[str, Any]]], bool],
) -> tuple[list[dict[str, Any]], MinimalityLevel]:
    if len(sequence) <= 1:
        return sequence, MinimalityLevel.LOCALLY_MINIMIZED

    current = list(sequence)
    changed = True
    while changed and len(current) > 1:
        changed = False
        for i in range(len(current)):
            trial = current[:i] + current[i + 1 :]
            if trial and still_falsifies(trial):
                current = trial
                changed = True
                break

    # Drop non-essential headers one at a time
    if len(current) == 1 and current[0].get("headers"):
        step = dict(current[0])
        headers = dict(step.get("headers") or {})
        for key in list(headers.keys()):
            trial_headers = {k: v for k, v in headers.items() if k != key}
            trial_step = {**step, "headers": trial_headers}
            if still_falsifies([trial_step]):
                step = trial_step
                headers = trial_headers
        current = [step]

    return current, MinimalityLevel.LOCALLY_MINIMIZED


__all__ = ["minimize_sequence"]
