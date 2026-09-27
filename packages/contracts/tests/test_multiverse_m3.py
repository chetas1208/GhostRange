import uuid

from ghostrange_contracts.enums import ReasonCode, ResourceClass, VerificationResult
from ghostrange_contracts.multiverse_m3 import (
    AttackReplayPlanV1,
    ForkStrategy,
    InvestigationBudgetV1,
    RemediationActionKind,
    RemediationActionV1,
    RemediationChangeType,
    RemediationPlanV1,
    SchedulerDecisionV2,
    VerificationSuiteV1,
    WorldEvaluationV1,
    WorldFingerprintV1,
    WorldForkV2,
)


def test_remediation_plan_validates():
    plan = RemediationPlanV1(
        title="Fix A",
        description="Tighten auth middleware",
        change_type=RemediationChangeType.MIDDLEWARE_POLICY,
        expected_effect="Reject bad tokens",
        estimated_runtime_seconds=120,
        estimated_cost_usd=0.05,
        source="fixture",
        actions=[
            RemediationActionV1(
                kind=RemediationActionKind.CONFIG_PATCH,
                target_asset_ids=[uuid.uuid4()],
                parameters={"file": "/etc/auth/policy.yaml"},
            )
        ],
    )
    assert plan.actions[0].kind == RemediationActionKind.CONFIG_PATCH


def test_world_fork_v2_lineage():
    base = uuid.uuid4()
    parent = uuid.uuid4()
    child = uuid.uuid4()
    rem = uuid.uuid4()
    fp = WorldFingerprintV1(world_id=parent, scenario_version="auth-lab-v1")
    fork = WorldForkV2(
        range_id=uuid.uuid4(),
        base_world_id=base,
        parent_world_id=parent,
        child_world_id=child,
        remediation_id=rem,
        fork_generation=1,
        fork_strategy=ForkStrategy.TEMPLATE_REPLAY,
        creation_reason="candidate remediation B",
        inherited_state_reference="sha256:abc",
        fork_point_fingerprint=fp,
        requested_resource_profile=ResourceClass.CPU_SMALL,
        created_by="orchestrator",
    )
    assert fork.fork_strategy == ForkStrategy.TEMPLATE_REPLAY


def test_scheduler_decision_v2_reason_codes():
    d = SchedulerDecisionV2(
        world_id=uuid.uuid4(),
        branch_decision="PRUNE",
        reason_codes=[ReasonCode.PRUNE_REMEDIATION_FAILED],
        explanation="Original attack still succeeds after remediation",
    )
    assert d.reason_codes[0] == ReasonCode.PRUNE_REMEDIATION_FAILED


def test_world_evaluation_dimensions():
    ev = WorldEvaluationV1(
        world_id=uuid.uuid4(),
        remediation_id=uuid.uuid4(),
        original_attack_blocked=True,
        regressions_passed=False,
        alternative_tests_passed=True,
        evidence_count=3,
        runtime_seconds=90,
        compute_cost_usd=0.12,
        verification_status=VerificationResult.FAILED,
        confidence_explanation="Regression suite failed on authorized login path",
    )
    assert not ev.regressions_passed
