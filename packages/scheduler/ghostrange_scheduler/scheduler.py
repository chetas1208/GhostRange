"""GhostScheduler v1 entrypoint.

    schedule(task, cluster_state, investigation_state) -> SchedulerDecisionV1

Deterministic: same (task, cluster_state, investigation_state, now) always
produces the same SchedulerDecisionV1 (modulo the decision's own random
``id`` and ``created_at``, which are metadata about *this call*, not
inputs to the decision logic -- pass ``now=`` explicitly in tests that
need bit-for-bit reproducibility of every field).

Explainable: every branch below ends by emitting >=1 ``ReasonCode`` from
the fixed, already-locked 10-value enum (``ghostrange_contracts.enums.ReasonCode``).
No new reason codes are invented here.

Not RL, not a neural scheduler, no LLM placement decision: every branch is
a plain, inspectable if/else over normalized numeric factors and a fixed
formula. See the package README for the full design writeup.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from ghostrange_contracts.cluster_state import BudgetStateV1, ClusterStateV1, WorldStateV1
from ghostrange_contracts.enums import ReasonCode, TaskStatus
from ghostrange_contracts.scheduler import SchedulerDecisionV1
from ghostrange_contracts.task import TaskV1

from .cost import PLACEHOLDER_RATE_CLASSES, estimate_cost_usd
from .normalize import NormalizedPriorityFactorsV1
from .parallelism import decide_parallelism
from .priority import DEFAULT_COST_FLOOR_USD, compute_priority
from .resource_selection import select_resource_class
from .stopping import DEFAULT_BASE_FLOOR_THRESHOLD, effective_stop, should_stop

# --- Tunable thresholds for reason-code emission on the "runnable, not
# being stopped" path. Each is a deliberately simple, documented constant
# -- no empirical calibration data exists yet (M2: one range, modest
# services), these are defensible round-number defaults, not fitted.
UNCERTAINTY_HIGH_THRESHOLD = 0.66
SECURITY_RISK_HIGH_THRESHOLD = 0.75  # matches SecurityCriticality.HIGH's mapped value
DEPENDENCY_CRITICALITY_HIGH_THRESHOLD = 0.66
CHEAP_COST_THRESHOLD_USD = 2 * DEFAULT_COST_FLOOR_USD
LOW_VALUE_PRIORITY_RAW_THRESHOLD = DEFAULT_BASE_FLOOR_THRESHOLD
STRAGGLER_MULTIPLIER = 1.5  # per SPECULATION.md §B: "exceeds ... p90 by ... 1.5x"

# Decision TTLs (SchedulerDecisionV1.expiration = now + ttl). Blocked/
# stopped decisions are re-checked soon because the gating condition
# (a dependency completing, budget freeing up, cancellation finishing)
# can change quickly; normal running/queued decisions get a longer TTL.
TTL_BLOCKED_SECONDS = 30
TTL_STOP_SECONDS = 30
TTL_NORMAL_SECONDS = 300


def _blocked_decision(
    task: TaskV1,
    reason_codes: list[ReasonCode],
    termination_condition: str,
    now,
    notes: Optional[str] = None,
) -> SchedulerDecisionV1:
    resource_class, _ = select_resource_class(task.resource_profile, None)
    return SchedulerDecisionV1(
        task_id=task.id,
        world_id=task.world_id,
        target_resource_class=resource_class,
        priority=0,
        estimated_cost_usd=0.0,
        expected_value=0.0,
        parallelism=1,
        speculative=False,
        reason_codes=reason_codes,
        constraints={"blocked": "true"},
        expiration=now + timedelta(seconds=TTL_BLOCKED_SECONDS),
        termination_condition=termination_condition,
        notes=notes,
    )


def schedule(
    task: TaskV1,
    cluster_state: ClusterStateV1,
    investigation_state: WorldStateV1,
    *,
    now=None,
) -> SchedulerDecisionV1:
    now = now or datetime.now(timezone.utc)
    budget_state: Optional[BudgetStateV1] = cluster_state.budget

    # --- Gate 1: BUDGET_EXHAUSTED. Hard ceiling, checked first and takes
    # precedence over everything else, including DEPENDENCY_CRITICAL --
    # per ADAPTIVE_COMPUTE.md §3.3's explicit precedence rule ("a
    # dependency being critical doesn't create money that doesn't exist").
    if budget_state is not None and budget_state.is_exhausted:
        return _blocked_decision(
            task,
            [ReasonCode.BUDGET_EXHAUSTED],
            "blocked: budget exhausted (hard_stop); re-evaluate if budget "
            "increases or committed spend is released",
            now,
        )

    # --- Gate 2: DEPENDENCY_CRITICAL (blocked). A task whose declared
    # dependencies are not all COMPLETED cannot run yet, regardless of how
    # attractive its priority would otherwise be.
    if not investigation_state.dependencies_satisfied(task.dependencies):
        return _blocked_decision(
            task,
            [ReasonCode.DEPENDENCY_CRITICAL],
            "blocked: one or more dependencies not yet COMPLETED; "
            "re-evaluate when dependency status changes",
            now,
        )

    # --- Runnable from here on: compute the shared inputs every remaining
    # branch needs (normalized factors, resource class, cost, priority).
    downstream_pending = investigation_state.count_downstream_pending(task.id)
    factors = NormalizedPriorityFactorsV1.from_raw(
        expected_evidence_gain=task.expected_evidence_gain,
        uncertainty=task.uncertainty,
        security_criticality=task.security_criticality,
        downstream_pending_count=downstream_pending,
    )
    resource_class, resource_reasons = select_resource_class(task.resource_profile, cluster_state)
    full_cost_estimate = estimate_cost_usd(resource_class, task.estimated_duration_seconds, cluster_state)
    priority_result = compute_priority(factors, full_cost_estimate)
    parallelism = decide_parallelism(task.task_type, resource_class, cluster_state)

    notes_parts: list[str] = []
    if resource_class in PLACEHOLDER_RATE_CLASSES and not cluster_state.rate_card_usd_per_hour.get(
        resource_class
    ):
        notes_parts.append(
            f"cost estimate uses a PLACEHOLDER rate-card entry for {resource_class.value} "
            "(see ghostrange_scheduler.cost); replace with observed Vultr pricing when available."
        )

    # --- Gate 3: stopping-function check, only meaningful for a task
    # that is already RUNNING and has live progress telemetry -- there is
    # nothing to "stop" for a task that hasn't started spending yet.
    progress = investigation_state.progress.get(task.id) if task.status == TaskStatus.RUNNING else None
    if progress is not None:
        g_hat = (
            progress.remaining_evidence_gain_estimate
            if progress.remaining_evidence_gain_estimate is not None
            else task.expected_evidence_gain
        )
        c_hat = (
            progress.remaining_cost_estimate_usd
            if progress.remaining_cost_estimate_usd is not None
            else max(task.estimated_cost_usd - progress.cost_spent_usd, 0.0)
        )
        stop_result = should_stop(
            g_hat,
            c_hat,
            factors.security_risk,
            factors.dependency_criticality,
            budget_state=budget_state,
        )
        downstream_blocked = investigation_state.downstream_blocked_without(task.id)
        actual_stop, veto_reason = effective_stop(
            stop_recommended=stop_result.stop,
            dependency_criticality=factors.dependency_criticality,
            downstream_blocked_without=downstream_blocked,
            budget_exhausted=False,  # already gated above; never re-triggers budget here
        )

        straggler = False
        stats = cluster_state.duration_stats.get(task.task_type)
        if stats is not None:
            straggler = progress.elapsed_seconds > stats.p90_seconds * STRAGGLER_MULTIPLIER

        if actual_stop:
            reasons = [ReasonCode.MARGINAL_GAIN_LOW]
            if straggler:
                reasons.append(ReasonCode.STRAGGLER_DETECTED)
            notes_parts.append(
                f"stopping function A: ratio={stop_result.ratio:.4f} < "
                f"floor={stop_result.threshold:.4f} (dominant factor: {stop_result.dominant_factor})"
            )
            return SchedulerDecisionV1(
                task_id=task.id,
                world_id=task.world_id,
                target_resource_class=resource_class,
                priority=0,
                estimated_cost_usd=0.0,
                expected_value=priority_result.expected_value,
                parallelism=1,
                speculative=False,
                reason_codes=reasons,
                constraints={"stop_recommended": "true"},
                expiration=now + timedelta(seconds=TTL_STOP_SECONDS),
                termination_condition=(
                    f"stop: marginal VoI ratio {stop_result.ratio:.4f} below floor "
                    f"{stop_result.threshold:.4f}; release resources for this task"
                ),
                notes="; ".join(notes_parts) or None,
            )

        if veto_reason == "dependency_veto":
            notes_parts.append(
                f"stopping function A recommended stop (ratio={stop_result.ratio:.4f} < "
                f"floor={stop_result.threshold:.4f}) but Function C vetoed it: a downstream "
                "task still depends on this one completing"
            )
            reasons = [ReasonCode.DEPENDENCY_CRITICAL]
            if straggler:
                reasons.append(ReasonCode.STRAGGLER_DETECTED)
            return SchedulerDecisionV1(
                task_id=task.id,
                world_id=task.world_id,
                target_resource_class=resource_class,
                priority=priority_result.priority_int,
                estimated_cost_usd=c_hat,
                expected_value=priority_result.expected_value,
                parallelism=1,
                speculative=task.speculation_policy.enabled,
                reason_codes=reasons,
                constraints={},
                expiration=now + timedelta(seconds=TTL_NORMAL_SECONDS),
                termination_condition="release when task.completed, task.failed, or dependency veto lifts",
                notes="; ".join(notes_parts) or None,
            )

        # stop_result.stop was False: ratio cleared the floor, continue.
        # Fall through to normal decision assembly below, but remember the
        # straggler/CHEAP_INFORMATION_GAIN signals from the ratio check.
        extra_reasons: list[ReasonCode] = []
        if straggler:
            extra_reasons.append(ReasonCode.STRAGGLER_DETECTED)
        if stop_result.dominant_factor == "cost" and stop_result.ratio >= 2 * stop_result.threshold:
            extra_reasons.append(ReasonCode.CHEAP_INFORMATION_GAIN)
        estimated_cost_for_decision = c_hat
    else:
        extra_reasons = []
        estimated_cost_for_decision = full_cost_estimate

    # --- Normal path: task is runnable (and, if running, not recommended
    # to stop). Assemble reason codes deterministically from the
    # normalized factors and priority result.
    reasons_set: dict[ReasonCode, None] = {}  # ordered-set via dict, Python 3.7+ preserves insertion order
    for code in resource_reasons:
        reasons_set[code] = None
    if factors.uncertainty >= UNCERTAINTY_HIGH_THRESHOLD:
        reasons_set[ReasonCode.HIGH_UNCERTAINTY] = None
    if factors.security_risk >= SECURITY_RISK_HIGH_THRESHOLD:
        reasons_set[ReasonCode.HIGH_ASSET_RISK] = None
    if factors.dependency_criticality >= DEPENDENCY_CRITICALITY_HIGH_THRESHOLD:
        reasons_set[ReasonCode.DEPENDENCY_CRITICAL] = None
    if full_cost_estimate <= CHEAP_COST_THRESHOLD_USD:
        reasons_set[ReasonCode.CHEAP_INFORMATION_GAIN] = None
    if priority_result.priority_raw < LOW_VALUE_PRIORITY_RAW_THRESHOLD:
        reasons_set[ReasonCode.BRANCH_LOW_VALUE] = None
    for code in extra_reasons:
        reasons_set[code] = None

    if not reasons_set:
        # Guaranteed-non-empty fallback (SchedulerDecisionV1.reason_codes
        # has min_length=1): no factor cleared any "notable" threshold, so
        # attribute the decision honestly to whether it's cost-effective
        # (CHEAP_INFORMATION_GAIN) or not (BRANCH_LOW_VALUE) rather than
        # mislabeling a merely-average factor as "HIGH_*".
        if priority_result.priority_raw >= LOW_VALUE_PRIORITY_RAW_THRESHOLD:
            reasons_set[ReasonCode.CHEAP_INFORMATION_GAIN] = None
        else:
            reasons_set[ReasonCode.BRANCH_LOW_VALUE] = None

    reason_codes = sorted(reasons_set.keys(), key=lambda c: c.value)

    return SchedulerDecisionV1(
        task_id=task.id,
        world_id=task.world_id,
        target_resource_class=resource_class,
        priority=priority_result.priority_int,
        estimated_cost_usd=estimated_cost_for_decision,
        expected_value=priority_result.expected_value,
        parallelism=parallelism,
        speculative=task.speculation_policy.enabled,
        reason_codes=reason_codes,
        constraints={},
        expiration=now + timedelta(seconds=TTL_NORMAL_SECONDS),
        termination_condition="release when task.completed, task.failed, task.cancelled, or this decision expires",
        notes="; ".join(notes_parts) or None,
    )


__all__ = ["schedule"]
