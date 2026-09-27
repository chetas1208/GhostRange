import uuid

from ghostrange_contracts.ghostgate_m11 import ApprovalDecisionKind, ApprovalDecisionV1, ProductionChangeCandidateV1, PromotionState
from ghostrange_contracts.ghostwatch_m12 import ExternalDeploymentRecordV1, ObservedDeploymentStateV1

from ghostrange_ghostwatch.adapters.mock import MockDeploymentExecutorAdapter
from ghostrange_ghostwatch.campaign import GhostWatch, StartCampaignInput


def _camp(gw):
    c = ProductionChangeCandidateV1(
        remediation_id=uuid.uuid4(),
        source_revision_id=uuid.uuid4(),
        twin_revision_id=uuid.uuid4(),
        experiment_id=uuid.uuid4(),
        evidence_root_digest="e",
        change_candidate_hash="hash1",
        state=PromotionState.APPROVED,
    )
    dec = ApprovalDecisionV1(
        request_id=uuid.uuid4(),
        change_candidate_hash="hash1",
        decision=ApprovalDecisionKind.APPROVED,
        approver_id="h",
    )
    return gw.start_campaign(
        StartCampaignInput(
            candidate=c,
            approval=dec,
            approved_artifact_digest="sha256:good",
            rollback_target_digest="sha256:old",
            adapter=MockDeploymentExecutorAdapter(approved_digest="sha256:good"),
        )
    )


def test_external_record_variance_holds():
    gw = GhostWatch()
    camp = _camp(gw)
    rec = ExternalDeploymentRecordV1(
        executor="generic",
        external_id="ext-1",
        campaign_id=camp.id,
        approved_change_hash="hash1",
        event_id="e1",
        sequence=1,
        observed_state=ObservedDeploymentStateV1(artifact_digest="sha256:evil"),
    )
    tick = gw.ingest_external(camp.id, rec)
    assert "deployment.variance_detected" in tick.events
    assert tick.state.value == "HOLD"
