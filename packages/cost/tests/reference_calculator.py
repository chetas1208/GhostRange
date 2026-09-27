"""Independent reference math for golden tests — NOT imported by production billing."""

from __future__ import annotations


def ref_billable_hours_one_hour_minimum(lifetime_seconds: int) -> int:
    if lifetime_seconds <= 0:
        return 0
    hours = (lifetime_seconds + 3599) // 3600
    return max(1, hours)


def ref_compute_cost_usd(hourly_p: float, lifetime_seconds: int) -> float:
    h = ref_billable_hours_one_hour_minimum(lifetime_seconds)
    return h * hourly_p


def ref_inference_usd(input_tokens: int, output_tokens: int, in_per_m: float, out_per_m: float) -> float:
    return (input_tokens * in_per_m + output_tokens * out_per_m) / 1_000_000
