"""GhostScheduler V3 plan entrypoint — emits SchedulingPlanV3."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml

from ghostrange_contracts.enums import ReasonCode
from ghostrange_contracts.scheduler_v3 import (
    InferenceRoute,
    PlanActionV1,
    SchedulerActionKind,
    SchedulerPolicyId,
    SchedulingContextV3,
    SchedulingPlanV3,
)
from ghostrange_contracts.task import TaskV1

from .critical_path import analyze_critical_path
from .placement import choose_resource_class, select_worker_best_fit, select_worker_first_fit
from .queue import compute_queue_state

_CONFIG_CACHE: dict[str, Any] | None = None


def load_config() -> dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    path = Path(__file__).resolve().parents[4] / "config" / "ghostscheduler-v3.yaml"
    if path.is_file():
        _CONFIG_CACHE = yaml.safe_load(path.read_text()) or {}
    else:
        _CONFIG_CACHE = {}
    return _CONFIG_CACHE


def _task_profile_map(ctx: SchedulingContextV3) -> dict[str, Any]:
    return {str(p.task_id): p for p in ctx.task_profiles}


def plan(ctx: SchedulingContextV3) -> SchedulingPlanV3:
    t0 = time.perf_counter()
    cfg = load_config()
    auto = cfg.get("autoscale", {})
    queue_cfg = cfg.get("queue", {})

    ctx.queue_state = compute_queue_state(ctx)
    actions: list[PlanActionV1] = []

    task_by_id: dict[str, TaskV1] = {str(t.id): t for t in ctx.tasks}
    profiles = _task_profile_map(ctx)
    task_type_by_id = {str(t.id): t.task_type.value for t in ctx.tasks}
    edges = [(str(a), str(b)) for a, b in ctx.dependency_edges]
    cp = analyze_critical_path([str(t.id) for t in ctx.tasks], edges, ctx.latency_model, task_type_by_id)

    # Scale-out when queue pressure high and budget allows
    scale_threshold = int(queue_cfg.get("scale_out_ready_threshold", 8))
    crit_threshold = int(queue_cfg.get("scale_out_critical_ready_threshold", 3))
    if (
        ctx.policy_id == SchedulerPolicyId.GHOSTSCHEDULER_V3
        and ctx.queue_state.ready_count >= scale_threshold
        and ctx.budget_remaining_usd > 0.5
    ):
        reasons = [ReasonCode.SCALE_OUT_QUEUE_PRESSURE]
        if ctx.queue_state.critical_ready_count >= crit_threshold:
            reasons.append(ReasonCode.SCALE_OUT_CRITICAL_PATH)
        actions.append(
            PlanActionV1(
                action=SchedulerActionKind.PROVISION_WORKER,
                target_id=ctx.range_id,
                reason_codes=reasons,
                input_features={
                    "ready_count": float(ctx.queue_state.ready_count),
                    "critical_ready": float(ctx.queue_state.critical_ready_count),
                },
                estimated_cost_usd=min(0.25, ctx.budget_remaining_usd),
                estimated_latency_seconds=float(
                    ctx.provider_startup_seconds.get("cpu", auto.get("minimum_worker_lifetime_seconds", 180))
                ),
                constraints_considered=["budget_remaining", "queue_pressure"],
                notes="scale-out tick",
            )
        )

    # Scale-in: idle workers past threshold
    idle_sec = float(auto.get("minimum_idle_period_seconds", 60))
    for w in ctx.workers:
        if w.state == "READY" and w.utilization < 0.05 and w.remaining_min_lifetime_seconds <= 0:
            actions.append(
                PlanActionV1(
                    action=SchedulerActionKind.DRAIN_WORKER,
                    target_id=w.worker_id,
                    worker_id=w.worker_id,
                    reason_codes=[ReasonCode.SCALE_IN_IDLE_CAPACITY],
                    input_features={"utilization": w.utilization, "idle_threshold": idle_sec},
                    estimated_benefit=w.estimated_hourly_cost_usd / 3600.0,
                    constraints_considered=["minimum_worker_lifetime", "not_busy"],
                )
            )

    # Place ready tasks
    for tid in ctx.ready_task_ids:
        tid_s = str(tid)
        task = task_by_id.get(tid_s)
        if task is None:
            continue
        prof = profiles.get(tid_s)
        timing = cp.get(tid_s)
        on_cp = timing.on_critical_path if timing else False

        if prof and prof.model_inference:
            actions.append(
                PlanActionV1(
                    action=SchedulerActionKind.ROUTE_INFERENCE,
                    target_id=task.id,
                    reason_codes=[ReasonCode.CHEAP_INFORMATION_GAIN],
                    inference_route=InferenceRoute.VULTR_SERVERLESS,
                    estimated_cost_usd=0.01,
                    input_features={"model_inference": 1.0},
                    constraints_considered=["no_deterministic_verification_to_llm"],
                )
            )
            continue

        if prof:
            rc, rc_reasons = choose_resource_class(prof)
        else:
            from ghostrange_contracts.enums import ResourceClass as RC

            rc, rc_reasons = RC.CPU_SMALL, [ReasonCode.CPU_SUFFICIENT]

        if ctx.policy_id == SchedulerPolicyId.FIRST_FIT:
            worker, w_reasons = select_worker_first_fit(prof, ctx.workers) if prof else (None, rc_reasons)
        elif ctx.policy_id == SchedulerPolicyId.COST_MIN:
            worker, w_reasons = select_worker_best_fit(prof, ctx.workers) if prof else (None, rc_reasons)
        else:
            worker, w_reasons = select_worker_best_fit(prof, ctx.workers) if prof else (None, rc_reasons)

        reasons = list(dict.fromkeys(rc_reasons + w_reasons))
        if on_cp:
            reasons.append(ReasonCode.DEPENDENCY_CRITICAL)

        est = ctx.latency_model.estimate_seconds(task.task_type)
        cost_rate = ctx.cost_model.worker_hourly(rc, 0.05)
        est_cost = cost_rate * (est / 3600.0)

        if est_cost > ctx.budget_remaining_usd:
            actions.append(
                PlanActionV1(
                    action=SchedulerActionKind.DEFER_TASK,
                    target_id=task.id,
                    reason_codes=[ReasonCode.BUDGET_EXHAUSTED],
                    estimated_cost_usd=est_cost,
                    constraints_considered=["budget_hard_cap"],
                )
            )
            continue

        actions.append(
            PlanActionV1(
                action=SchedulerActionKind.PLACE_TASK,
                target_id=task.id,
                worker_id=worker.worker_id if worker else None,
                resource_class=rc,
                reason_codes=reasons,
                input_features={
                    "on_critical_path": 1.0 if on_cp else 0.0,
                    "slack_seconds": timing.slack_seconds if timing else 0.0,
                },
                estimated_cost_usd=est_cost,
                estimated_latency_seconds=est,
                confidence=0.7 if worker else 0.4,
                constraints_considered=["mandatory_tests", "world_isolation", "resource_fit"],
            )
        )

    # Optional exploration stop (never for mandatory tasks)
    marginal_floor = float(cfg.get("stopping", {}).get("optional_exploration_marginal_gain_floor", 0.05))
    for world_id in ctx.branch_world_ids:
        gain = ctx.evidence_gain_per_branch.get(str(world_id), 1.0)
        if gain < marginal_floor:
            actions.append(
                PlanActionV1(
                    action=SchedulerActionKind.STOP_EXPLORATION,
                    target_id=world_id,
                    reason_codes=[ReasonCode.STOP_MARGINAL_GAIN_LOW],
                    input_features={"evidence_gain": gain, "floor": marginal_floor},
                    constraints_considered=["optional_only", "mandatory_tests_never_skipped"],
                )
            )

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return SchedulingPlanV3(
        range_id=ctx.range_id,
        policy_id=ctx.policy_id,
        actions=actions,
        planning_duration_ms=elapsed_ms,
    )


__all__ = ["plan", "load_config"]
