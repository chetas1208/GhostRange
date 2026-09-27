import uuid
from datetime import datetime, timedelta, timezone

import pytest
from ghostrange_contracts.enums import (
    AgentType,
    ComputeProvider,
    ReasonCode,
    ResourceClass,
    TaskType,
    VerificationMethod,
)

from ghostrange_contracts.enums import ExecutionStatus

from ghostrange_events import (
    AgentActionV1,
    AgentCompletedV1,
    AgentStartedV1,
    ComputeProvisioningV1,
    ComputeReadyV1,
    ComputeReleasedV1,
    ComputeRequestedV1,
    EvidenceCreatedV1,
    ExecutionAuthorizedV1,
    ExecutionCompletedV1,
    ExecutionDeniedV1,
    ExecutionRequestedV1,
    ExecutionStartedV1,
    RangeAuthorizedV1,
    RangeRequestedV1,
    RangeValidatedV1,
    SchedulerDecisionV1Event,
    TaskCancelledV1,
    TaskCompletedV1,
    TaskCreatedV1,
    TaskFailedV1,
    TaskQueuedV1,
    TaskScheduledV1,
    TaskSpeculatedV1,
    TaskStartedV1,
    VerificationFailedV1,
    VerificationPassedV1,
    VerificationStartedV1,
    WorldDestroyingV1,
    WorldDestroyedV1,
    WorldForkedV1,
    WorldProvisioningV1,
    WorldReadyV1,
    WorldRequestedV1,
)
from ghostrange_events.names import EventName
from ghostrange_events.registry import parse_event


def _future() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=5)


# One realistic instance per registered event, keyed by EventName so the
# parametrized test below can assert every EventName is covered, not just
# "however many examples someone remembered to write".
EXAMPLES: dict[EventName, object] = {
    EventName.RANGE_REQUESTED: RangeRequestedV1(
        range_id=uuid.uuid4(), spec_id=uuid.uuid4(), requested_by="chetasparekh2003@gmail.com"
    ),
    EventName.RANGE_VALIDATED: RangeValidatedV1(
        range_id=uuid.uuid4(), spec_id=uuid.uuid4(), valid=True
    ),
    EventName.RANGE_AUTHORIZED: RangeAuthorizedV1(
        range_id=uuid.uuid4(),
        spec_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        budget_id=uuid.uuid4(),
        authorized_by="auto-policy",
    ),
    EventName.WORLD_REQUESTED: WorldRequestedV1(
        world_id=uuid.uuid4(), range_id=uuid.uuid4(), requested_by="orchestrator"
    ),
    EventName.WORLD_PROVISIONING: WorldProvisioningV1(
        world_id=uuid.uuid4(), range_id=uuid.uuid4()
    ),
    EventName.WORLD_READY: WorldReadyV1(
        world_id=uuid.uuid4(), range_id=uuid.uuid4(), asset_count=5, network_count=2
    ),
    EventName.WORLD_FORKED: WorldForkedV1(
        range_id=uuid.uuid4(),
        parent_world_id=uuid.uuid4(),
        child_world_id=uuid.uuid4(),
        fork_reason="trying two competing remediations",
        created_by="scheduler",
    ),
    EventName.WORLD_DESTROYING: WorldDestroyingV1(
        world_id=uuid.uuid4(), range_id=uuid.uuid4(), reason="teardown"
    ),
    EventName.WORLD_DESTROYED: WorldDestroyedV1(
        world_id=uuid.uuid4(), range_id=uuid.uuid4(), reason="verification complete"
    ),
    EventName.TASK_CREATED: TaskCreatedV1(
        task_id=uuid.uuid4(), world_id=uuid.uuid4(), task_type=TaskType.INVESTIGATE,
        created_by="orchestrator",
    ),
    EventName.TASK_QUEUED: TaskQueuedV1(
        task_id=uuid.uuid4(), world_id=uuid.uuid4(), task_type=TaskType.INVESTIGATE, priority=3
    ),
    EventName.TASK_SCHEDULED: TaskScheduledV1(
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        decision_id=uuid.uuid4(),
        target_resource_class=ResourceClass.CPU_MEDIUM,
    ),
    EventName.TASK_STARTED: TaskStartedV1(
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        compute_worker_id=uuid.uuid4(),
    ),
    EventName.TASK_COMPLETED: TaskCompletedV1(
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        duration_seconds=42.5,
        actual_cost_usd=0.12,
        evidence_ids=[uuid.uuid4()],
    ),
    EventName.TASK_FAILED: TaskFailedV1(
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        error_message="ssh timeout",
        retry_count=1,
        will_retry=True,
    ),
    EventName.TASK_SPECULATED: TaskSpeculatedV1(
        task_id=uuid.uuid4(),
        parent_task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        speculative_branch_index=0,
        reason="cheap information gain while primary path is uncertain",
    ),
    EventName.TASK_CANCELLED: TaskCancelledV1(
        task_id=uuid.uuid4(), world_id=uuid.uuid4(), reason="superseded by another candidate",
        cancelled_by="scheduler",
    ),
    EventName.EXECUTION_REQUESTED: ExecutionRequestedV1(
        execution_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        requested_by="scheduler",
        target_asset_ids=[uuid.uuid4()],
    ),
    EventName.EXECUTION_AUTHORIZED: ExecutionAuthorizedV1(
        execution_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        target_asset_ids=[uuid.uuid4()],
    ),
    EventName.EXECUTION_DENIED: ExecutionDeniedV1(
        execution_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        reason="target asset not in Range's active Policy allowlist",
        offending_asset_ids=[uuid.uuid4()],
    ),
    EventName.EXECUTION_STARTED: ExecutionStartedV1(
        execution_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        compute_worker_id=uuid.uuid4(),
        command="atomic-red-team T1059.001",
    ),
    EventName.EXECUTION_COMPLETED: ExecutionCompletedV1(
        execution_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        status=ExecutionStatus.SUCCEEDED,
        exit_code=0,
        duration_seconds=12.4,
        artifact_ids=[uuid.uuid4()],
    ),
    EventName.AGENT_STARTED: AgentStartedV1(
        agent_id=uuid.uuid4(), world_id=uuid.uuid4(), agent_type=AgentType.INVESTIGATOR
    ),
    EventName.AGENT_ACTION: AgentActionV1(
        agent_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        action_type="shell_command",
        target="dc01.corp.local",
    ),
    EventName.AGENT_COMPLETED: AgentCompletedV1(
        agent_id=uuid.uuid4(), world_id=uuid.uuid4(), outcome="hypothesis_supported"
    ),
    EventName.EVIDENCE_CREATED: EvidenceCreatedV1(
        evidence_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        claim_id=uuid.uuid4(),
        verification_id=uuid.uuid4(),
        artifact_ids=[uuid.uuid4()],
        content_hash="a" * 64,
    ),
    EventName.VERIFICATION_STARTED: VerificationStartedV1(
        verification_id=uuid.uuid4(),
        claim_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        method=VerificationMethod.ADVERSARIAL_ATTACK,
        verifier_agent_id=uuid.uuid4(),
    ),
    EventName.VERIFICATION_PASSED: VerificationPassedV1(
        verification_id=uuid.uuid4(),
        claim_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        evidence_ids=[uuid.uuid4()],
    ),
    EventName.VERIFICATION_FAILED: VerificationFailedV1(
        verification_id=uuid.uuid4(),
        claim_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        reason="attack succeeded against the remediated world",
    ),
    EventName.COMPUTE_REQUESTED: ComputeRequestedV1(
        compute_worker_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        resource_class=ResourceClass.GPU_SMALL,
        region="ewr",
        requested_by="scheduler",
    ),
    EventName.COMPUTE_PROVISIONING: ComputeProvisioningV1(
        compute_worker_id=uuid.uuid4(), provider=ComputeProvider.VULTR, region="ewr"
    ),
    EventName.COMPUTE_READY: ComputeReadyV1(
        compute_worker_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        resource_class=ResourceClass.GPU_SMALL,
        region="ewr",
        provider=ComputeProvider.VULTR,
        provider_instance_id="vultr-instance-abc123",
        cost_per_hour_usd=0.90,
    ),
    EventName.COMPUTE_RELEASED: ComputeReleasedV1(
        compute_worker_id=uuid.uuid4(), total_cost_usd=1.35, reason="task completed"
    ),
    EventName.SCHEDULER_DECISION: SchedulerDecisionV1Event(
        decision_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        target_resource_class=ResourceClass.GPU_LARGE,
        priority=9,
        estimated_cost_usd=4.5,
        expected_value=0.95,
        parallelism=1,
        speculative=False,
        reason_codes=[ReasonCode.GPU_ACCELERATION_EXPECTED, ReasonCode.HIGH_ASSET_RISK],
        expiration=_future(),
        termination_condition="release on task.completed",
    ),
}


def test_examples_cover_every_event_name():
    assert set(EXAMPLES.keys()) == set(EventName)


@pytest.mark.parametrize("event_name", list(EventName))
def test_roundtrip_via_own_model_validate_json(event_name):
    instance = EXAMPLES[event_name]
    cls = type(instance)
    raw_json = instance.model_dump_json()
    rehydrated = cls.model_validate_json(raw_json)
    assert rehydrated == instance


@pytest.mark.parametrize("event_name", list(EventName))
def test_roundtrip_via_registry_dispatch(event_name):
    instance = EXAMPLES[event_name]
    raw_json = instance.model_dump_json()
    rehydrated = parse_event(raw_json)
    assert rehydrated == instance
    assert rehydrated.event_name == event_name


@pytest.mark.parametrize("event_name", list(EventName))
def test_roundtrip_via_dict_not_just_json_string(event_name):
    instance = EXAMPLES[event_name]
    as_dict = instance.model_dump(mode="json")
    rehydrated = parse_event(as_dict)
    assert rehydrated == instance
