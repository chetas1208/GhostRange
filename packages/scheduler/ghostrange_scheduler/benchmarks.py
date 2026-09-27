"""Reusable benchmark fixture set: a handful of representative
(TaskV1, ClusterStateV1, WorldStateV1) combinations with their expected
SchedulerDecisionV1 shape, for this package's own tests AND for other
agents/wave-3 (E2E, integration status) testing to reuse rather than
re-inventing fixtures.

Each ``BenchmarkCase`` is fully deterministic: constructing the same case
twice and calling ``schedule()`` with the same ``now`` produces bit-for-bit
identical decisions (modulo ``id``/``created_at``, which are per-call
metadata, not decision content).

Usage from another package/test suite::

    from ghostrange_scheduler.benchmarks import ALL_CASES
    from ghostrange_scheduler import schedule

    for case in ALL_CASES:
        decision = schedule(case.task, case.cluster_state, case.world_state, now=case.now)
        assert case.expected_reason_codes <= set(decision.reason_codes)
        assert decision.priority == case.expected_priority  # if asserting exact priority
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from ghostrange_contracts.cluster_state import (
    BudgetStateV1,
    ClusterStateV1,
    TaskDurationStatsV1,
    TaskProgressV1,
    WorldStateV1,
)
from ghostrange_contracts.enums import (
    ReasonCode,
    ResourceClass,
    SecurityCriticality,
    TaskStatus,
    TaskType,
)
from ghostrange_contracts.policy import BudgetV1
from ghostrange_contracts.task import ResourceProfileV1, SpeculationPolicyV1, TaskV1

FIXED_NOW = datetime(2026, 9, 26, 12, 0, 0, tzinfo=timezone.utc)

# Fixed ids so every case is reproducible byte-for-byte across runs/processes
# (uuid4() is random; a benchmark fixture set needs stable ids so a
# consumer can hardcode expectations against specific task_id/world_id
# values if they want to, e.g. in a golden-file test).
RANGE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
WORLD_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    description: str
    task: TaskV1
    cluster_state: ClusterStateV1
    world_state: WorldStateV1
    now: datetime
    expected_reason_codes: frozenset[ReasonCode]
    expected_priority_is_zero: bool
    expected_resource_class: ResourceClass | None = None  # None = don't assert


def _profile(**overrides) -> ResourceProfileV1:
    defaults = dict(cpu_cores=2.0, memory_gb=4.0)
    defaults.update(overrides)
    return ResourceProfileV1(**defaults)


def _base_cluster(**overrides) -> ClusterStateV1:
    defaults = dict(
        range_id=RANGE_ID,
        as_of=FIXED_NOW,
        capacity={
            ResourceClass.CPU_SMALL: 4,
            ResourceClass.CPU_MEDIUM: 2,
            ResourceClass.CPU_LARGE: 1,
        },
        in_use={},
    )
    defaults.update(overrides)
    return ClusterStateV1(**defaults)


def _base_world(**overrides) -> WorldStateV1:
    defaults = dict(world_id=WORLD_ID, range_id=RANGE_ID, as_of=FIXED_NOW)
    defaults.update(overrides)
    return WorldStateV1(**defaults)


# --- Case 1: ordinary runnable CPU_SMALL task, no dependencies, no
# special risk/uncertainty -- the "happy path, nothing remarkable" case
# that exercises the guaranteed-non-empty reason-code fallback.
_case1_task = TaskV1(
    id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
    world_id=WORLD_ID,
    task_type=TaskType.INVESTIGATE,
    resource_profile=_profile(),
    estimated_duration_seconds=300,
    estimated_cost_usd=0.05,
    uncertainty=0.3,
    expected_evidence_gain=0.4,
    security_criticality=SecurityCriticality.LOW,
)
CASE_ORDINARY_CPU_SMALL = BenchmarkCase(
    name="ordinary_cpu_small",
    description="Runnable, no dependencies, low risk/uncertainty, small resource profile.",
    task=_case1_task,
    cluster_state=_base_cluster(),
    world_state=_base_world(),
    now=FIXED_NOW,
    expected_reason_codes=frozenset({ReasonCode.CHEAP_INFORMATION_GAIN}),
    expected_priority_is_zero=False,
    expected_resource_class=ResourceClass.CPU_SMALL,
)


# --- Case 2: blocked on an unfinished dependency.
_dep_id = uuid.UUID("10000000-0000-0000-0000-0000000000d1")
_case2_task = TaskV1(
    id=uuid.UUID("10000000-0000-0000-0000-000000000002"),
    world_id=WORLD_ID,
    task_type=TaskType.VERIFY,
    resource_profile=_profile(),
    estimated_duration_seconds=120,
    estimated_cost_usd=0.02,
    uncertainty=0.2,
    expected_evidence_gain=0.5,
    dependencies=[_dep_id],
)
CASE_BLOCKED_ON_DEPENDENCY = BenchmarkCase(
    name="blocked_on_dependency",
    description="Dependency not yet COMPLETED -- must be blocked, not scheduled.",
    task=_case2_task,
    cluster_state=_base_cluster(),
    world_state=_base_world(task_status={_dep_id: TaskStatus.RUNNING}),
    now=FIXED_NOW,
    expected_reason_codes=frozenset({ReasonCode.DEPENDENCY_CRITICAL}),
    expected_priority_is_zero=True,
)


# --- Case 3: budget exhausted -- must block regardless of task quality.
_case3_task = TaskV1(
    id=uuid.UUID("10000000-0000-0000-0000-000000000003"),
    world_id=WORLD_ID,
    task_type=TaskType.ATTACK,
    resource_profile=_profile(),
    estimated_duration_seconds=600,
    estimated_cost_usd=0.3,
    uncertainty=0.9,
    expected_evidence_gain=0.95,
    security_criticality=SecurityCriticality.CRITICAL,
)
_case3_budget = BudgetV1(
    range_id=RANGE_ID, max_total_cost_usd=50.0, spent_cost_usd=50.0, max_duration_seconds=7200
)
CASE_BUDGET_EXHAUSTED = BenchmarkCase(
    name="budget_exhausted",
    description="High-value task, but the Range's budget is exhausted -- BUDGET_EXHAUSTED "
    "must override even a high expected-evidence-gain / high-risk / high-uncertainty task.",
    task=_case3_task,
    cluster_state=_base_cluster(budget=BudgetStateV1(budget=_case3_budget, as_of=FIXED_NOW)),
    world_state=_base_world(),
    now=FIXED_NOW,
    expected_reason_codes=frozenset({ReasonCode.BUDGET_EXHAUSTED}),
    expected_priority_is_zero=True,
)


# --- Case 4: GPU-required task, GPU capacity available.
_case4_task = TaskV1(
    id=uuid.UUID("10000000-0000-0000-0000-000000000004"),
    world_id=WORLD_ID,
    task_type=TaskType.ANALYZE,
    resource_profile=_profile(gpu_required=True, gpu_type="A100"),
    estimated_duration_seconds=1800,
    estimated_cost_usd=1.5,
    uncertainty=0.5,
    expected_evidence_gain=0.6,
)
CASE_GPU_AVAILABLE = BenchmarkCase(
    name="gpu_available",
    description="GPU-required task with GPU capacity free -- expect GPU_ACCELERATION_EXPECTED.",
    task=_case4_task,
    cluster_state=_base_cluster(capacity={**_base_cluster().capacity, ResourceClass.GPU_SMALL: 1}),
    world_state=_base_world(),
    now=FIXED_NOW,
    expected_reason_codes=frozenset({ReasonCode.GPU_ACCELERATION_EXPECTED}),
    expected_priority_is_zero=False,
    expected_resource_class=ResourceClass.GPU_SMALL,
)


# --- Case 5: GPU-required task, NO GPU capacity in the cluster -> falls
# back to CPU and flags GPU_NOT_JUSTIFIED.
_case5_task = TaskV1(
    id=uuid.UUID("10000000-0000-0000-0000-000000000005"),
    world_id=WORLD_ID,
    task_type=TaskType.ANALYZE,
    resource_profile=_profile(gpu_required=True),
    estimated_duration_seconds=1800,
    estimated_cost_usd=1.5,
    uncertainty=0.5,
    expected_evidence_gain=0.6,
)
CASE_GPU_UNAVAILABLE = BenchmarkCase(
    name="gpu_unavailable_fallback",
    description="GPU-required task, zero GPU capacity in cluster -- must fall back to a CPU "
    "class and flag GPU_NOT_JUSTIFIED, not block outright.",
    task=_case5_task,
    cluster_state=_base_cluster(),  # no GPU_SMALL/GPU_LARGE capacity entries
    world_state=_base_world(),
    now=FIXED_NOW,
    expected_reason_codes=frozenset({ReasonCode.GPU_NOT_JUSTIFIED}),
    expected_priority_is_zero=False,
    expected_resource_class=ResourceClass.CPU_SMALL,
)


# --- Case 6: running task whose remaining marginal value has collapsed
# -- stopping function A should fire MARGINAL_GAIN_LOW.
_case6_task = TaskV1(
    id=uuid.UUID("10000000-0000-0000-0000-000000000006"),
    world_id=WORLD_ID,
    task_type=TaskType.ANALYZE,
    resource_profile=_profile(),
    estimated_duration_seconds=1200,
    estimated_cost_usd=5.0,
    uncertainty=0.1,
    expected_evidence_gain=0.05,
    status=TaskStatus.RUNNING,
)
_case6_progress = TaskProgressV1(
    task_id=_case6_task.id,
    started_at=FIXED_NOW,
    elapsed_seconds=1000,
    cost_spent_usd=4.0,
    evidence_accumulated=0.04,
    remaining_cost_estimate_usd=4.0,
    remaining_evidence_gain_estimate=0.01,
)
CASE_RUNNING_MARGINAL_GAIN_LOW = BenchmarkCase(
    name="running_marginal_gain_low",
    description="Running task, remaining evidence gain has collapsed relative to remaining "
    "cost -- Function A should recommend stopping, no dependency veto applies.",
    task=_case6_task,
    cluster_state=_base_cluster(),
    world_state=_base_world(progress={_case6_task.id: _case6_progress}),
    now=FIXED_NOW,
    expected_reason_codes=frozenset({ReasonCode.MARGINAL_GAIN_LOW}),
    expected_priority_is_zero=True,
)


# --- Case 7: same collapsing-value running task as Case 6, but with 2+
# pending downstream dependents -- Function C's dependency veto should
# keep it alive (DEPENDENCY_CRITICAL) instead of stopping it.
_case7_dependent_a = uuid.UUID("10000000-0000-0000-0000-0000000000d2")
_case7_dependent_b = uuid.UUID("10000000-0000-0000-0000-0000000000d3")
CASE_RUNNING_DEPENDENCY_VETO = BenchmarkCase(
    name="running_dependency_veto",
    description="Same collapsing-value running task as case 6, but 2 pending downstream "
    "dependents push dependency_criticality above the veto threshold -- Function C keeps "
    "it alive (DEPENDENCY_CRITICAL) instead of stopping it.",
    task=_case6_task,
    cluster_state=_base_cluster(),
    world_state=_base_world(
        progress={_case6_task.id: _case6_progress},
        downstream_dependents={_case6_task.id: [_case7_dependent_a, _case7_dependent_b]},
        task_status={_case7_dependent_a: TaskStatus.QUEUED, _case7_dependent_b: TaskStatus.QUEUED},
    ),
    now=FIXED_NOW,
    expected_reason_codes=frozenset({ReasonCode.DEPENDENCY_CRITICAL}),
    expected_priority_is_zero=False,
)


# --- Case 8: running task exceeding its task_type's p90 duration by more
# than the straggler multiplier -- STRAGGLER_DETECTED, but still cost-
# effective enough to continue (not stopped).
_case8_task = TaskV1(
    id=uuid.UUID("10000000-0000-0000-0000-000000000008"),
    world_id=WORLD_ID,
    task_type=TaskType.ATTACK,
    resource_profile=_profile(),
    estimated_duration_seconds=300,
    estimated_cost_usd=0.1,
    uncertainty=0.6,
    expected_evidence_gain=0.7,
    status=TaskStatus.RUNNING,
)
_case8_progress = TaskProgressV1(
    task_id=_case8_task.id,
    started_at=FIXED_NOW,
    elapsed_seconds=500,  # p90 is 200s below; 500 > 200*1.5=300 -> straggler
    cost_spent_usd=0.05,
    remaining_cost_estimate_usd=0.02,
    remaining_evidence_gain_estimate=0.6,
)
CASE_RUNNING_STRAGGLER = BenchmarkCase(
    name="running_straggler_but_worth_continuing",
    description="Running ATTACK task well past its task_type's p90*1.5 elapsed threshold -- "
    "STRAGGLER_DETECTED fires, but remaining value/cost is still good enough that Function A "
    "does not recommend stopping.",
    task=_case8_task,
    cluster_state=_base_cluster(
        duration_stats={
            TaskType.ATTACK: TaskDurationStatsV1(task_type=TaskType.ATTACK, p50_seconds=100, p90_seconds=200, sample_count=25)
        }
    ),
    world_state=_base_world(progress={_case8_task.id: _case8_progress}),
    now=FIXED_NOW,
    expected_reason_codes=frozenset({ReasonCode.STRAGGLER_DETECTED}),
    expected_priority_is_zero=False,
)


# --- Case 9: high uncertainty + high security criticality, expensive
# enough not to be "cheap" -- exercises HIGH_UNCERTAINTY + HIGH_ASSET_RISK
# co-firing without CHEAP_INFORMATION_GAIN.
_case9_task = TaskV1(
    id=uuid.UUID("10000000-0000-0000-0000-000000000009"),
    world_id=WORLD_ID,
    task_type=TaskType.REMEDIATE,
    resource_profile=_profile(cpu_cores=6, memory_gb=16),
    estimated_duration_seconds=3600,
    estimated_cost_usd=2.0,
    uncertainty=0.9,
    expected_evidence_gain=0.85,
    security_criticality=SecurityCriticality.CRITICAL,
)
CASE_HIGH_RISK_HIGH_UNCERTAINTY = BenchmarkCase(
    name="high_risk_high_uncertainty",
    description="CRITICAL security_criticality + high uncertainty, moderate cost -- expect "
    "both HIGH_ASSET_RISK and HIGH_UNCERTAINTY, high priority.",
    task=_case9_task,
    cluster_state=_base_cluster(),
    world_state=_base_world(),
    now=FIXED_NOW,
    expected_reason_codes=frozenset({ReasonCode.HIGH_ASSET_RISK, ReasonCode.HIGH_UNCERTAINTY}),
    expected_priority_is_zero=False,
    expected_resource_class=ResourceClass.CPU_MEDIUM,
)


# --- Case 10: PROVISION task type -- must always serialize (parallelism=1)
# regardless of free cluster capacity.
_case10_task = TaskV1(
    id=uuid.UUID("10000000-0000-0000-0000-000000000010"),
    world_id=WORLD_ID,
    task_type=TaskType.PROVISION,
    resource_profile=_profile(),
    estimated_duration_seconds=120,
    estimated_cost_usd=0.03,
    uncertainty=0.2,
    expected_evidence_gain=0.3,
)
CASE_PROVISION_SERIALIZES = BenchmarkCase(
    name="provision_serializes",
    description="PROVISION task type must serialize (parallelism == 1) even with plenty of "
    "free CPU_SMALL capacity in the cluster.",
    task=_case10_task,
    cluster_state=_base_cluster(),
    world_state=_base_world(),
    now=FIXED_NOW,
    expected_reason_codes=frozenset({ReasonCode.CHEAP_INFORMATION_GAIN}),
    expected_priority_is_zero=False,
    expected_resource_class=ResourceClass.CPU_SMALL,
)


ALL_CASES: list[BenchmarkCase] = [
    CASE_ORDINARY_CPU_SMALL,
    CASE_BLOCKED_ON_DEPENDENCY,
    CASE_BUDGET_EXHAUSTED,
    CASE_GPU_AVAILABLE,
    CASE_GPU_UNAVAILABLE,
    CASE_RUNNING_MARGINAL_GAIN_LOW,
    CASE_RUNNING_DEPENDENCY_VETO,
    CASE_RUNNING_STRAGGLER,
    CASE_HIGH_RISK_HIGH_UNCERTAINTY,
    CASE_PROVISION_SERIALIZES,
]

__all__ = [
    "FIXED_NOW",
    "RANGE_ID",
    "WORLD_ID",
    "BenchmarkCase",
    "CASE_ORDINARY_CPU_SMALL",
    "CASE_BLOCKED_ON_DEPENDENCY",
    "CASE_BUDGET_EXHAUSTED",
    "CASE_GPU_AVAILABLE",
    "CASE_GPU_UNAVAILABLE",
    "CASE_RUNNING_MARGINAL_GAIN_LOW",
    "CASE_RUNNING_DEPENDENCY_VETO",
    "CASE_RUNNING_STRAGGLER",
    "CASE_HIGH_RISK_HIGH_UNCERTAINTY",
    "CASE_PROVISION_SERIALIZES",
    "ALL_CASES",
]
