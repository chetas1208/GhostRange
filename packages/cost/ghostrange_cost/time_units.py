"""Explicit time conversions — avoid magic 3600 scattered in billing code."""

from __future__ import annotations

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 60 * SECONDS_PER_MINUTE


def seconds_to_hours_ceiling(seconds: int) -> int:
    if seconds <= 0:
        return 0
    return (seconds + SECONDS_PER_HOUR - 1) // SECONDS_PER_HOUR


def seconds_elapsed(start_epoch: float, end_epoch: float) -> int:
    if end_epoch < start_epoch:
        return 0
    return int(end_epoch - start_epoch)
