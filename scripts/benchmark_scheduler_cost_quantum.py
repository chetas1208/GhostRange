#!/usr/bin/env python3
"""Compare old per-second vs quantum cost for scheduler benchmark durations."""

from __future__ import annotations

from ghostrange_contracts.enums import ResourceClass
from ghostrange_scheduler.benchmarks import ALL_CASES
from ghostrange_scheduler.cost import estimate_cost_usd

SECONDS_PER_HOUR = 3600.0


def legacy_estimate(class_: ResourceClass, seconds: float, rate: float) -> float:
    return rate * (seconds / SECONDS_PER_HOUR)


def main() -> None:
    from ghostrange_scheduler.cost import hourly_rate_usd

    rows = []
    for case in ALL_CASES[:8]:
        task = case.task
        sec = float(task.estimated_duration_seconds)
        rc = task.resource_profile.preferred_resource_class or ResourceClass.CPU_MEDIUM
        rate = hourly_rate_usd(rc, case.cluster_state)
        old = legacy_estimate(rc, sec, rate)
        new = estimate_cost_usd(rc, sec, case.cluster_state)
        rows.append((task.task_type, sec, old, new))

    print("task_type\tduration_s\tlegacy_usd\tquantum_usd\tratio")
    for task_type, sec, old, new in rows:
        ratio = (new / old) if old > 1e-9 else float("inf")
        print(f"{task_type}\t{sec:.0f}\t{old:.6f}\t{new:.6f}\t{ratio:.2f}")


if __name__ == "__main__":
    main()
