import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from ghostrange_contracts.enums import ReasonCode, ResourceClass
from ghostrange_contracts.scheduler import SchedulerDecisionV1


def _future(seconds: int = 300) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def test_valid_scheduler_decision_constructs():
    decision = SchedulerDecisionV1(
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        target_resource_class=ResourceClass.GPU_SMALL,
        priority=5,
        estimated_cost_usd=1.25,
        expected_value=0.9,
        parallelism=2,
        speculative=True,
        reason_codes=[ReasonCode.GPU_ACCELERATION_EXPECTED, ReasonCode.HIGH_UNCERTAINTY],
        expiration=_future(),
        termination_condition="release when task.completed or expiration reached",
    )
    assert decision.schema_version == "1"
    assert ReasonCode.GPU_ACCELERATION_EXPECTED in decision.reason_codes


def test_scheduler_decision_requires_at_least_one_reason_code():
    with pytest.raises(ValidationError):
        SchedulerDecisionV1(
            task_id=uuid.uuid4(),
            world_id=uuid.uuid4(),
            target_resource_class=ResourceClass.CPU_SMALL,
            priority=1,
            estimated_cost_usd=0.1,
            expected_value=0.1,
            reason_codes=[],
            expiration=_future(),
            termination_condition="n/a",
        )


def test_scheduler_decision_rejects_unknown_reason_code():
    with pytest.raises(ValidationError):
        SchedulerDecisionV1(
            task_id=uuid.uuid4(),
            world_id=uuid.uuid4(),
            target_resource_class=ResourceClass.CPU_SMALL,
            priority=1,
            estimated_cost_usd=0.1,
            expected_value=0.1,
            reason_codes=["NOT_A_REAL_CODE"],
            expiration=_future(),
            termination_condition="n/a",
        )


def test_scheduler_decision_requires_aware_datetime_for_expiration():
    with pytest.raises(ValidationError):
        SchedulerDecisionV1(
            task_id=uuid.uuid4(),
            world_id=uuid.uuid4(),
            target_resource_class=ResourceClass.CPU_SMALL,
            priority=1,
            estimated_cost_usd=0.1,
            expected_value=0.1,
            reason_codes=[ReasonCode.CHEAP_INFORMATION_GAIN],
            expiration=datetime.now(),  # naive, no tzinfo
            termination_condition="n/a",
        )
