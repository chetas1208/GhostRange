"""Task attribution — analytical only; must not double-count campaign totals."""

from __future__ import annotations

from ghostrange_cost.money import add_micros


def attribute_wall_time_share(
    *,
    resource_total_usd_micros: int,
    task_durations_seconds: dict[str, int],
) -> dict[str, int]:
    """Split resource cost by wall-time share across tasks on same VM."""
    total_sec = sum(max(0, s) for s in task_durations_seconds.values())
    if total_sec <= 0 or resource_total_usd_micros <= 0:
        return {tid: 0 for tid in task_durations_seconds}
    out: dict[str, int] = {}
    allocated = 0
    items = list(task_durations_seconds.items())
    for i, (tid, sec) in enumerate(items):
        if i == len(items) - 1:
            out[tid] = resource_total_usd_micros - allocated
        else:
            share = (resource_total_usd_micros * max(0, sec)) // total_sec
            out[tid] = share
            allocated = add_micros(allocated, share)
    return out


def campaign_total_from_resources(resource_totals_usd_micros: list[int]) -> int:
    """Unique billable resources — sum each resource once."""
    return add_micros(*resource_totals_usd_micros)
