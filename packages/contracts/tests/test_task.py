import uuid

import pytest
from pydantic import ValidationError

from ghostrange_contracts.enums import ResourceClass, TaskStatus, TaskType
from ghostrange_contracts.task import (
    ResourceProfileV1,
    RetryPolicyV1,
    SpeculationPolicyV1,
    TaskV1,
)


def _profile(**overrides) -> ResourceProfileV1:
    defaults = dict(cpu_cores=2, memory_gb=4)
    defaults.update(overrides)
    return ResourceProfileV1(**defaults)


def test_valid_task_constructs():
    task = TaskV1(
        world_id=uuid.uuid4(),
        task_type=TaskType.INVESTIGATE,
        resource_profile=_profile(),
        estimated_duration_seconds=120,
        estimated_cost_usd=0.50,
        uncertainty=0.3,
        expected_evidence_gain=0.8,
    )
    assert task.status == TaskStatus.QUEUED
    assert task.dependencies == []
    assert task.retry_policy.max_retries == 0
    assert task.speculation_policy.enabled is False


def test_task_rejects_uncertainty_out_of_range():
    with pytest.raises(ValidationError):
        TaskV1(
            world_id=uuid.uuid4(),
            task_type=TaskType.INVESTIGATE,
            resource_profile=_profile(),
            estimated_duration_seconds=120,
            estimated_cost_usd=0.5,
            uncertainty=1.5,
            expected_evidence_gain=0.8,
        )


def test_task_rejects_negative_cost():
    with pytest.raises(ValidationError):
        TaskV1(
            world_id=uuid.uuid4(),
            task_type=TaskType.INVESTIGATE,
            resource_profile=_profile(),
            estimated_duration_seconds=120,
            estimated_cost_usd=-1,
            uncertainty=0.1,
            expected_evidence_gain=0.8,
        )


def test_resource_profile_gpu_type_requires_gpu_required():
    with pytest.raises(ValidationError):
        _profile(gpu_required=False, gpu_type="A100")


def test_resource_profile_gpu_type_allowed_with_gpu_required():
    profile = _profile(gpu_required=True, gpu_type="A100")
    assert profile.gpu_type == "A100"


def test_resource_profile_preferred_resource_class():
    profile = _profile(preferred_resource_class=ResourceClass.GPU_LARGE)
    assert profile.preferred_resource_class == ResourceClass.GPU_LARGE


def test_retry_policy_bounds():
    with pytest.raises(ValidationError):
        RetryPolicyV1(max_retries=21)


def test_speculation_policy_defaults():
    policy = SpeculationPolicyV1()
    assert policy.enabled is False
    assert policy.max_speculative_branches == 1
    assert policy.cancel_on_primary_success is True


def test_task_status_assignment_is_validated():
    task = TaskV1(
        world_id=uuid.uuid4(),
        task_type=TaskType.VERIFY,
        resource_profile=_profile(),
        estimated_duration_seconds=10,
        estimated_cost_usd=0.1,
        uncertainty=0.1,
        expected_evidence_gain=0.1,
    )
    task.status = TaskStatus.RUNNING
    assert task.status == TaskStatus.RUNNING
    with pytest.raises(ValidationError):
        task.status = "NOT_A_REAL_STATUS"
