"""Scheduler-facing cost estimates — uses ghostrange_cost billing quanta."""

from __future__ import annotations

from ghostrange_contracts.cluster_state import ClusterStateV1
from ghostrange_contracts.enums import ResourceClass
from ghostrange_cost.compute_billing import (
    compute_ephemeral_cost_usd_micros,
    incremental_cost_new_worker_usd_micros,
    incremental_cost_reuse_task_usd_micros,
)
from ghostrange_cost.money import micros_to_usd_decimal, usd_to_micros
from ghostrange_cost.time_units import SECONDS_PER_HOUR
from ghostrange_cost.vultr_policy import DEFAULT_VULTR_POLICY

SECONDS_PER_HOUR_FLOAT = float(SECONDS_PER_HOUR)

# [PLACEHOLDER / RESEARCH-DERIVED unit costs, USD per hour]
DEFAULT_RATE_CARD_USD_PER_HOUR: dict[ResourceClass, float] = {
    ResourceClass.CPU_SMALL: 0.0042,
    ResourceClass.CPU_MEDIUM: 0.03,
    ResourceClass.CPU_LARGE: 0.12,
    ResourceClass.GPU_SMALL: 1.00,
    ResourceClass.GPU_LARGE: 2.99,
}

PLACEHOLDER_RATE_CLASSES = frozenset(
    {ResourceClass.CPU_MEDIUM, ResourceClass.CPU_LARGE, ResourceClass.GPU_SMALL}
)


def hourly_rate_usd(resource_class: ResourceClass, cluster_state: ClusterStateV1 | None) -> float:
    if cluster_state is not None:
        observed = cluster_state.rate_card_usd_per_hour.get(resource_class)
        if observed is not None:
            return observed
    return DEFAULT_RATE_CARD_USD_PER_HOUR[resource_class]


def estimate_cost_usd(
    resource_class: ResourceClass,
    estimated_duration_seconds: float,
    cluster_state: ClusterStateV1 | None = None,
) -> float:
    """
    Estimated **incremental** cost assuming a **new** billable worker (Vultr min quantum).

    NOT linear seconds/3600*rate — see ghostrange_cost.compute_billing.
    """
    if estimated_duration_seconds < 0:
        raise ValueError("estimated_duration_seconds must be >= 0")
    if estimated_duration_seconds == 0:
        return 0.0
    rate = hourly_rate_usd(resource_class, cluster_state)
    lifetime = max(int(estimated_duration_seconds), DEFAULT_VULTR_POLICY.minimum_billing_unit_seconds)
    result = compute_ephemeral_cost_usd_micros(hourly_rate_usd=str(rate), provider_lifetime_seconds=lifetime)
    return float(micros_to_usd_decimal(result.total_usd_micros))


def estimate_marginal_new_worker_usd(
    resource_class: ResourceClass,
    cluster_state: ClusterStateV1 | None = None,
) -> float:
    """One additional minimum billing quantum (scheduling scale-out)."""
    rate = hourly_rate_usd(resource_class, cluster_state)
    micros = incremental_cost_new_worker_usd_micros(str(rate))
    return float(micros_to_usd_decimal(micros))


def estimate_marginal_reuse_usd(
    resource_class: ResourceClass,
    *,
    worker_committed_usd: float,
    seconds_into_quantum: int,
    task_duration_seconds: float,
    cluster_state: ClusterStateV1 | None = None,
) -> float:
    rate = hourly_rate_usd(resource_class, cluster_state)
    micros = incremental_cost_reuse_task_usd_micros(
        worker_committed_usd_micros=usd_to_micros(str(worker_committed_usd)),
        seconds_into_current_quantum=seconds_into_quantum,
        task_duration_estimate_seconds=int(task_duration_seconds),
        hourly_rate_usd=str(rate),
    )
    return float(micros_to_usd_decimal(micros))


__all__ = [
    "DEFAULT_RATE_CARD_USD_PER_HOUR",
    "PLACEHOLDER_RATE_CLASSES",
    "hourly_rate_usd",
    "estimate_cost_usd",
    "estimate_marginal_new_worker_usd",
    "estimate_marginal_reuse_usd",
    "SECONDS_PER_HOUR_FLOAT",
]
