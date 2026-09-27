import uuid

import pytest

from ghostrange_contracts.cluster_state import ClusterStateV1, WorldStateV1
from ghostrange_contracts.enums import ResourceClass, TaskStatus, TaskType
from ghostrange_contracts.task import ResourceProfileV1, TaskV1
from ghostrange_scheduler import schedule
from ghostrange_scheduler.benchmarks import ALL_CASES


@pytest.mark.parametrize("case", ALL_CASES, ids=[c.name for c in ALL_CASES])
def test_benchmark_case_produces_expected_reason_codes(case):
    decision = schedule(case.task, case.cluster_state, case.world_state, now=case.now)
    assert case.expected_reason_codes <= set(decision.reason_codes), (
        f"case {case.name}: expected {case.expected_reason_codes} to be a subset of "
        f"{decision.reason_codes}"
    )


@pytest.mark.parametrize("case", ALL_CASES, ids=[c.name for c in ALL_CASES])
def test_benchmark_case_priority_zero_expectation(case):
    decision = schedule(case.task, case.cluster_state, case.world_state, now=case.now)
    assert (decision.priority == 0) == case.expected_priority_is_zero


@pytest.mark.parametrize(
    "case", [c for c in ALL_CASES if c.expected_resource_class is not None], ids=lambda c: c.name
)
def test_benchmark_case_resource_class(case):
    decision = schedule(case.task, case.cluster_state, case.world_state, now=case.now)
    assert decision.target_resource_class == case.expected_resource_class


@pytest.mark.parametrize("case", ALL_CASES, ids=[c.name for c in ALL_CASES])
def test_benchmark_case_decision_is_deterministic(case):
    d1 = schedule(case.task, case.cluster_state, case.world_state, now=case.now)
    d2 = schedule(case.task, case.cluster_state, case.world_state, now=case.now)
    # id and created_at are per-call metadata; everything else must match
    # exactly for identical inputs.
    dump1 = d1.model_dump(exclude={"id", "created_at"})
    dump2 = d2.model_dump(exclude={"id", "created_at"})
    assert dump1 == dump2


@pytest.mark.parametrize("case", ALL_CASES, ids=[c.name for c in ALL_CASES])
def test_benchmark_case_always_has_at_least_one_reason_code(case):
    decision = schedule(case.task, case.cluster_state, case.world_state, now=case.now)
    assert len(decision.reason_codes) >= 1


def test_blocked_decision_has_short_expiration_for_quick_reevaluation():
    from ghostrange_scheduler.benchmarks import CASE_BLOCKED_ON_DEPENDENCY as case

    decision = schedule(case.task, case.cluster_state, case.world_state, now=case.now)
    assert (decision.expiration - case.now).total_seconds() <= 60


def test_dependency_blocked_task_never_gets_positive_priority():
    world_id = uuid.uuid4()
    range_id = uuid.uuid4()
    dep_id = uuid.uuid4()
    task = TaskV1(
        world_id=world_id,
        task_type=TaskType.VERIFY,
        resource_profile=ResourceProfileV1(cpu_cores=2, memory_gb=4),
        estimated_duration_seconds=100,
        estimated_cost_usd=0.1,
        uncertainty=0.9,
        expected_evidence_gain=0.99,  # even a very attractive task
        dependencies=[dep_id],
    )
    cluster = ClusterStateV1(range_id=range_id, capacity={ResourceClass.CPU_SMALL: 10})
    world = WorldStateV1(world_id=world_id, range_id=range_id, task_status={dep_id: TaskStatus.QUEUED})
    decision = schedule(task, cluster, world)
    assert decision.priority == 0
    assert decision.estimated_cost_usd == 0.0


def test_running_task_without_progress_telemetry_is_scheduled_normally():
    # A task marked RUNNING but with no WorldStateV1.progress entry (e.g.
    # telemetry hasn't posted yet) must not crash -- falls through to the
    # ordinary decision path.
    world_id = uuid.uuid4()
    range_id = uuid.uuid4()
    task = TaskV1(
        world_id=world_id,
        task_type=TaskType.ANALYZE,
        resource_profile=ResourceProfileV1(cpu_cores=2, memory_gb=4),
        estimated_duration_seconds=100,
        estimated_cost_usd=0.1,
        uncertainty=0.5,
        expected_evidence_gain=0.5,
        status=TaskStatus.RUNNING,
    )
    cluster = ClusterStateV1(range_id=range_id, capacity={ResourceClass.CPU_SMALL: 10})
    world = WorldStateV1(world_id=world_id, range_id=range_id)
    decision = schedule(task, cluster, world)
    assert decision.priority >= 0
    assert len(decision.reason_codes) >= 1


def test_unknown_dependency_status_is_treated_as_unsatisfied_fail_closed():
    world_id = uuid.uuid4()
    range_id = uuid.uuid4()
    dep_id = uuid.uuid4()
    task = TaskV1(
        world_id=world_id,
        task_type=TaskType.VERIFY,
        resource_profile=ResourceProfileV1(cpu_cores=2, memory_gb=4),
        estimated_duration_seconds=100,
        estimated_cost_usd=0.1,
        uncertainty=0.5,
        expected_evidence_gain=0.5,
        dependencies=[dep_id],
    )
    cluster = ClusterStateV1(range_id=range_id, capacity={ResourceClass.CPU_SMALL: 10})
    world = WorldStateV1(world_id=world_id, range_id=range_id, task_status={})  # dep_id unknown
    decision = schedule(task, cluster, world)
    assert decision.priority == 0
