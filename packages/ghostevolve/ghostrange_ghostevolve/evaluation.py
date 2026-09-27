"""Temporal evaluation, regression, forgetting — no future leakage."""

from __future__ import annotations

from dataclasses import dataclass

from ghostrange_contracts.ghostevolve_m18 import (
    ExperienceRecordV1,
    ForgettingReportV1,
)

from .runtime_estimator import M15RuntimeEstimatorChampion, RuntimeEstimatorCandidate


@dataclass
class RegressionResult:
    passed: bool
    mae_champion: float
    mae_candidate: float
    old_workload_mae_delta: float
    slice_regressions: dict[str, float]
    reason: str = ""


def temporal_train_test_split(
    records: list[ExperienceRecordV1],
    *,
    train_fraction: float = 0.7,
) -> tuple[list[ExperienceRecordV1], list[ExperienceRecordV1]]:
    ordered = sorted(records, key=lambda r: r.recorded_at)
    if len(ordered) < 4:
        return ordered, []
    cut = max(1, int(len(ordered) * train_fraction))
    return ordered[:cut], ordered[cut:]


def _mae(records: list[ExperienceRecordV1], predictor) -> float:
    if not records:
        return 0.0
    err = 0.0
    for rec in records:
        tc = str(rec.context.get("task_class", "default"))
        prior = float(rec.predictions.get("prior_seconds", 30.0))
        pred = predictor.predict(task_class=tc, prior_seconds=prior)
        actual = float(rec.actual_outcome["runtime_seconds"])
        err += abs(pred - actual)
    return err / len(records)


def evaluate_runtime_candidate(
    train: list[ExperienceRecordV1],
    test_future: list[ExperienceRecordV1],
    test_old_holdout: list[ExperienceRecordV1],
    *,
    max_old_workload_regression_ratio: float = 0.15,
    max_slice_cost_regression: float = 2.0,
) -> tuple[RuntimeEstimatorCandidate, RegressionResult]:
    champion = M15RuntimeEstimatorChampion()
    candidate = RuntimeEstimatorCandidate()
    candidate.train(train)

    if not test_future:
        return candidate, RegressionResult(
            passed=False,
            mae_champion=0.0,
            mae_candidate=0.0,
            old_workload_mae_delta=0.0,
            slice_regressions={},
            reason="INSUFFICIENT_DATA",
        )

    mae_c = _mae(test_future, champion)
    mae_k = _mae(test_future, candidate)
    old_c = _mae(test_old_holdout, champion) if test_old_holdout else mae_c
    old_k = _mae(test_old_holdout, candidate) if test_old_holdout else mae_k
    old_delta = old_k - old_c

    slice_regs: dict[str, float] = {}
    for rec in test_old_holdout:
        tc = str(rec.context.get("task_class", "default"))
        prior = float(rec.predictions.get("prior_seconds", 30.0))
        actual = float(rec.actual_outcome["runtime_seconds"])
        delta = abs(candidate.predict(task_class=tc, prior_seconds=prior) - actual) - abs(
            champion.predict(task_class=tc, prior_seconds=prior) - actual
        )
        slice_regs[tc] = slice_regs.get(tc, 0.0) + delta

    improved_future = mae_k <= mae_c
    old_ok = old_delta <= max_old_workload_regression_ratio * max(old_c, 1e-6)
    burst_ok = slice_regs.get("bursty_cpu", 0.0) <= max_slice_cost_regression * len(test_old_holdout or [])

    passed = improved_future and old_ok and burst_ok
    reason = ""
    if not improved_future:
        reason = "NO_IMPROVEMENT_ON_FUTURE_HOLDOUT"
    elif not old_ok:
        reason = "CATASTROPHIC_FORGETTING_OLD_WORKLOAD"
    elif not burst_ok:
        reason = "SLICE_REGRESSION_BURSY_CPU"

    return candidate, RegressionResult(
        passed=passed,
        mae_champion=mae_c,
        mae_candidate=mae_k,
        old_workload_mae_delta=old_delta,
        slice_regressions=slice_regs,
        reason=reason,
    )


def forgetting_report(
    candidate_version: str,
    champion_version: str,
    result: RegressionResult,
    *,
    budget: float = 0.15,
) -> ForgettingReportV1:
    return ForgettingReportV1(
        candidate_version=candidate_version,
        champion_version=champion_version,
        old_workload_metric_delta=result.old_workload_mae_delta,
        acceptable_regression_budget=budget,
        passed=result.old_workload_mae_delta <= budget,
        slices=result.slice_regressions,
    )
