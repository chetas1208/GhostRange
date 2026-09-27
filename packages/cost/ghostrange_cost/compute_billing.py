"""Compute instance billing — hourly quantum, not per-second proration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ghostrange_cost.money import add_micros, usd_to_micros
from ghostrange_cost.time_units import SECONDS_PER_HOUR, seconds_to_hours_ceiling
from ghostrange_cost.vultr_policy import DEFAULT_VULTR_POLICY, VultrBillingPolicySnapshot, VultrProductClass


@dataclass(frozen=True)
class ComputeBillableResult:
    billable_hours: int
    provider_lifetime_seconds: int
    hourly_rate_usd_micros: int
    total_usd_micros: int
    policy_version: str
    notes: str


def billable_hours_for_lifetime(
    provider_lifetime_seconds: int,
    *,
    policy: VultrBillingPolicySnapshot = DEFAULT_VULTR_POLICY,
) -> int:
    """Minimum one-hour quantum per Vultr server policy (when lifetime > 0)."""
    if provider_lifetime_seconds <= 0:
        return 0
    hours = seconds_to_hours_ceiling(provider_lifetime_seconds)
    if policy.minimum_billing_unit_seconds >= SECONDS_PER_HOUR:
        return max(1, hours)
    return hours


def compute_ephemeral_cost_usd_micros(
    *,
    hourly_rate_usd: str,
    provider_lifetime_seconds: int,
    product_class: VultrProductClass = VultrProductClass.CLOUD_COMPUTE_STANDARD,
    policy: VultrBillingPolicySnapshot = DEFAULT_VULTR_POLICY,
) -> ComputeBillableResult:
    """
    Authoritative estimate for ephemeral VM cost under pinned Vultr rules.

    NOT: lifetime_seconds / 3600 * rate (wrong for minimum quantum).
    """
    rate_micros = usd_to_micros(hourly_rate_usd)
    hours = billable_hours_for_lifetime(provider_lifetime_seconds, policy=policy)
    total = hours * rate_micros
    cap_note = ""
    if product_class == VultrProductClass.CLOUD_COMPUTE_STANDARD:
        cap_note = f"; monthly cap {policy.monthly_cap_hours_standard}h applies at invoice"
    elif product_class in (VultrProductClass.CLOUD_GPU, VultrProductClass.VX1):
        cap_note = f"; monthly cap {policy.monthly_cap_hours_gpu}h applies at invoice"
    return ComputeBillableResult(
        billable_hours=hours,
        provider_lifetime_seconds=provider_lifetime_seconds,
        hourly_rate_usd_micros=rate_micros,
        total_usd_micros=total,
        policy_version=policy.policy_version,
        notes=f"billable_hours={hours} (min quantum {policy.minimum_billing_unit_seconds}s){cap_note}",
    )


def incremental_cost_new_worker_usd_micros(
    hourly_rate_usd: str,
    *,
    policy: VultrBillingPolicySnapshot = DEFAULT_VULTR_POLICY,
) -> int:
    """Marginal cost of provisioning another worker (one new minimum quantum)."""
    rate_micros = usd_to_micros(hourly_rate_usd)
    return rate_micros  # one hour minimum


def incremental_cost_reuse_task_usd_micros(
    *,
    worker_committed_usd_micros: int,
    seconds_into_current_quantum: int,
    task_duration_estimate_seconds: int,
    hourly_rate_usd: str,
    policy: VultrBillingPolicySnapshot = DEFAULT_VULTR_POLICY,
) -> int:
    """
    Future incremental compute cost for scheduling: reuse within committed quantum ≈ 0.
    """
    quantum = policy.minimum_billing_unit_seconds
    remaining_in_quantum = max(0, quantum - seconds_into_current_quantum)
    if task_duration_estimate_seconds <= remaining_in_quantum:
        return 0
    # Task spans into next quantum — at most one additional hour at marginal rate
    rate_micros = usd_to_micros(hourly_rate_usd)
    extra_hours = seconds_to_hours_ceiling(task_duration_estimate_seconds - remaining_in_quantum)
    return extra_hours * rate_micros


def provider_lifetime_seconds(
    *,
    provider_created_at: datetime | None,
    as_of: datetime | None = None,
    provider_destroyed_at: datetime | None = None,
) -> int:
    if provider_created_at is None:
        return 0
    start = provider_created_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if provider_destroyed_at is not None:
        end = provider_destroyed_at
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
    else:
        end = as_of or datetime.now(timezone.utc)
    return max(0, int((end - start).total_seconds()))


def accrue_running_resource_usd_micros(
    *,
    hourly_rate_usd_micros: int,
    provider_lifetime_seconds: int,
    destroy_requested: bool,
    provider_destroyed: bool,
    policy: VultrBillingPolicySnapshot = DEFAULT_VULTR_POLICY,
) -> tuple[int, str]:
    """
    Accrued estimate while resource may still be billing.
    If destroy requested but not confirmed, do not reduce below committed quantum.
    """
    hours = billable_hours_for_lifetime(provider_lifetime_seconds, policy=policy)
    accrued = hours * hourly_rate_usd_micros
    if destroy_requested and not provider_destroyed:
        return accrued, "BILLING_END_UNCONFIRMED"
    if not provider_destroyed:
        return accrued, "ACTIVE"
    return accrued, "FINALIZED"
