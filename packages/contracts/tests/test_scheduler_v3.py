import uuid

from ghostrange_contracts.enums import ReasonCode, TaskType
from ghostrange_contracts.scheduler_v3 import (
    PlanActionV1,
    SchedulerActionKind,
    SchedulerPolicyId,
    SchedulingContextV3,
    SchedulingPlanV3,
    TaskResourceProfileV2,
)


def test_scheduling_plan_v3_constructs():
    rid = uuid.uuid4()
    plan = SchedulingPlanV3(
        range_id=rid,
        policy_id=SchedulerPolicyId.GHOSTSCHEDULER_V3,
        actions=[
            PlanActionV1(
                action=SchedulerActionKind.PLACE_TASK,
                target_id=uuid.uuid4(),
                reason_codes=[ReasonCode.CPU_SUFFICIENT],
            )
        ],
    )
    assert plan.schema_version == "3"


def test_task_resource_profile_v2_gpu_requires_memory_when_set():
    p = TaskResourceProfileV2(
        task_id=uuid.uuid4(),
        task_type=TaskType.VERIFY,
        cpu_min=1,
        cpu_preferred=2,
        ram_min_gb=1,
        ram_preferred_gb=2,
        gpu_required=True,
        gpu_memory_gb=16,
        expected_runtime_seconds=10,
    )
    assert p.gpu_required is True


def test_scheduling_context_v3_budget_fields():
    ctx = SchedulingContextV3(
        range_id=uuid.uuid4(),
        budget_remaining_usd=5.0,
        budget_hard_cap_usd=10.0,
    )
    assert ctx.schema_version == "3"
