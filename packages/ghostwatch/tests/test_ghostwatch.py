import uuid

import pytest

from ghostrange_contracts.ghostgate_m11 import ApprovalDecisionKind, ApprovalDecisionV1, ProductionChangeCandidateV1, PromotionState
from ghostrange_contracts.ghostwatch_m12 import DeploymentAuthorityMode, GateEvaluationStatus

from ghostrange_ghostwatch.adapters.mock import MockDeploymentExecutorAdapter
from ghostrange_ghostwatch.authority import block_model_escalation, may_request_control, control_globally_disabled
from ghostrange_ghostwatch.campaign import GhostWatch, StartCampaignInput
from ghostrange_ghostwatch.canary_analysis import analyze_stage
from ghostrange_ghostwatch.conformance import compare_deployment
from ghostrange_ghostwatch.simulator import ProductionRolloutSimulator, SimScenario
from ghostrange_contracts.ghostwatch_m12 import ConformanceStatus, ExecutorCapability, ObservedDeploymentStateV1, RolloutStageKind


def _approved_candidate() -> ProductionChangeCandidateV1:
    c = ProductionChangeCandidateV1(
        remediation_id=uuid.uuid4(),
        source_revision_id=uuid.uuid4(),
        twin_revision_id=uuid.uuid4(),
        experiment_id=uuid.uuid4(),
        evidence_root_digest="e",
        change_candidate_hash="hash1",
        state=PromotionState.APPROVED,
    )
    return c


def _approval() -> ApprovalDecisionV1:
    return ApprovalDecisionV1(
        request_id=uuid.uuid4(),
        change_candidate_hash="hash1",
        decision=ApprovalDecisionKind.APPROVED,
        approver_id="human-1",
    )


def test_default_observe_only_blocks_rollback_invoke():
    assert not may_request_control(DeploymentAuthorityMode.OBSERVE_ONLY, ExecutorCapability.REQUEST_ROLLBACK)


def test_unapproved_variance_holds():
    conf = compare_deployment(
        "sha256:good",
        ObservedDeploymentStateV1(artifact_digest="sha256:bad"),
    )
    assert conf.status == ConformanceStatus.MATERIAL_DIFFERENCE
    analysis = analyze_stage(
        RolloutStageKind.CANARY_10,
        conformance=conf,
        health=GateEvaluationStatus.PASS,
        security=GateEvaluationStatus.PASS,
        error_rate=GateEvaluationStatus.PASS,
        latency=GateEvaluationStatus.PASS,
    )
    assert analysis.outcome.value == "HOLD"


def test_missing_telemetry_not_pass():
    from ghostrange_contracts.ghostwatch_m12 import DeploymentConformanceReportV1

    conf = DeploymentConformanceReportV1(
        approved_artifact_digest="a",
        observed_artifact_digest="a",
        status=ConformanceStatus.MATCH,
    )
    analysis = analyze_stage(
        RolloutStageKind.CANARY_25,
        conformance=conf,
        health=GateEvaluationStatus.INSUFFICIENT_DATA,
        security=GateEvaluationStatus.PASS,
        error_rate=GateEvaluationStatus.PASS,
        latency=GateEvaluationStatus.PASS,
    )
    assert analysis.outcome.value == "HOLD"


def test_preauthorized_rollback():
    gw = GhostWatch()
    adapter = MockDeploymentExecutorAdapter(
        approved_digest="sha256:auth-v2.7",
        rollback_digest="sha256:auth-v2.6",
    )
    camp = gw.start_campaign(
        StartCampaignInput(
            candidate=_approved_candidate(),
            approval=_approval(),
            approved_artifact_digest="sha256:auth-v2.7",
            rollback_target_digest="sha256:auth-v2.6",
            authority_mode=DeploymentAuthorityMode.PREAUTHORIZED_ROLLBACK,
            adapter=adapter,
        )
    )
    tick = gw.maybe_invoke_rollback(camp.id, adapter=adapter, target_digest="sha256:auth-v2.6")
    assert "rollback.verified" in tick.events


def test_model_cannot_escalate():
    with pytest.raises(PermissionError):
        block_model_escalation("MODEL")


def test_good_canary_simulator_advances():
    results = ProductionRolloutSimulator().run_scenario(SimScenario.GOOD_CANARY)
    assert any(r.analysis_outcome == "ADVANCE" for r in results)


def test_bad_security_recommends_rollback():
    results = ProductionRolloutSimulator().run_scenario(SimScenario.BAD_SECURITY)
    assert any(r.analysis_outcome == "ROLLBACK_RECOMMENDED" for r in results)
