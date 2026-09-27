"""Warm worker retention vs new provisioning — billing quantum aware."""

from __future__ import annotations

from dataclasses import dataclass

from ghostrange_cost.compute_billing import incremental_cost_new_worker_usd_micros, incremental_cost_reuse_task_usd_micros
from ghostrange_cost.money import micros_to_usd_decimal
from ghostrange_cost.time_units import SECONDS_PER_HOUR
from ghostrange_cost.vultr_policy import DEFAULT_VULTR_POLICY

from ghostrange_contracts.enums import ResourceClass

from .cost import hourly_rate_usd


@dataclass(frozen=True)
class WarmRetentionDecisionV1:
    retain: bool
    reason: str
    incremental_reuse_usd: float
    incremental_new_worker_usd: float
    seconds_to_billing_boundary: int


def decide_warm_retention(
    *,
    resource_class: ResourceClass,
    idle_seconds: int,
    seconds_into_billing_quantum: int,
    predicted_next_task_seconds: int,
    cluster_state=None,
) -> WarmRetentionDecisionV1:
    rate = hourly_rate_usd(resource_class, cluster_state)
    reuse_micros = incremental_cost_reuse_task_usd_micros(
        worker_committed_usd_micros=0,
        seconds_into_current_quantum=seconds_into_billing_quantum,
        task_duration_estimate_seconds=predicted_next_task_seconds,
        hourly_rate_usd=str(rate),
    )
    new_micros = incremental_cost_new_worker_usd_micros(str(rate))
    boundary = max(0, DEFAULT_VULTR_POLICY.minimum_billing_unit_seconds - seconds_into_billing_quantum)
    retain = reuse_micros < new_micros or (idle_seconds < boundary and predicted_next_task_seconds > 0)
    reason = "LOW_INCREMENTAL_REUSE" if reuse_micros < new_micros else "BOUNDARY_OR_IDLE"
    return WarmRetentionDecisionV1(
        retain=retain,
        reason=reason,
        incremental_reuse_usd=float(micros_to_usd_decimal(reuse_micros)),
        incremental_new_worker_usd=float(micros_to_usd_decimal(new_micros)),
        seconds_to_billing_boundary=boundary,
    )
