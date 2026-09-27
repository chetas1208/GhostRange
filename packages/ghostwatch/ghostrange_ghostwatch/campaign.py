"""GhostWatch campaign lifecycle."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ghostrange_contracts.ghostgate_m11 import ApprovalDecisionV1, ProductionChangeCandidateV1
from ghostrange_contracts.ghostwatch_m12 import (
    ApprovedRollbackTargetV1,
    CanaryAnalysisV1,
    DeploymentAuthorityMode,
    DeploymentExecutionStatus,
    DeploymentExecutionV1,
    DeploymentObservationAttestationV1,
    ExecutorCapability,
    GhostWatchCampaignState,
    GhostWatchCampaignV1,
    ProductionEvidenceV1,
    ProductionSurpriseV1,
    RolloutStageKind,
    TwinPredictionV1,
    ConformanceStatus,
)
from ghostrange_contracts._base import utc_now

from .adapters.mock import MockDeploymentExecutorAdapter
from .authority import may_request_control, validate_approval_for_control
from .conformance import compare_deployment
from .surprise import detect_surprise


@dataclass
class StartCampaignInput:
    candidate: ProductionChangeCandidateV1
    approval: ApprovalDecisionV1
    approved_artifact_digest: str
    rollback_target_digest: str
    authority_mode: DeploymentAuthorityMode = DeploymentAuthorityMode.OBSERVE_ONLY
    adapter: Optional[MockDeploymentExecutorAdapter] = None
    correlation_id: str = ""


@dataclass
class TickResult:
    state: GhostWatchCampaignState
    events: list[str] = field(default_factory=list)


class GhostWatch:
    def __init__(self) -> None:
        self._campaigns: dict[uuid.UUID, GhostWatchCampaignV1] = {}
        self._evidence: dict[uuid.UUID, list[ProductionEvidenceV1]] = {}
        self._surprises: dict[uuid.UUID, list[ProductionSurpriseV1]] = {}
        self._seen_external_events: dict[uuid.UUID, set[str]] = {}

    def start_campaign(self, inp: StartCampaignInput) -> GhostWatchCampaignV1:
        validate_approval_for_control(inp.approval, inp.candidate.change_candidate_hash)

        execution = DeploymentExecutionV1(
            promotion_candidate_id=inp.candidate.id,
            approval_decision_id=inp.approval.id,
            approved_change_hash=inp.candidate.change_candidate_hash,
            approved_rollback_hash=inp.rollback_target_digest,
            executor=inp.adapter.adapter_id if inp.adapter else "pending",
            executor_type=inp.adapter.adapter_id if inp.adapter else "pending",
            authority_mode=inp.authority_mode,
            correlation_id=inp.correlation_id or hashlib.sha256(str(inp.candidate.id).encode()).hexdigest()[:16],
            environment_reference=inp.adapter.capabilities.environment_label if inp.adapter else "UNKNOWN",
        )
        rollback_target = ApprovedRollbackTargetV1(
            revision=inp.rollback_target_digest,
            artifact_digest=inp.rollback_target_digest,
        )
        camp = GhostWatchCampaignV1(
            promotion_candidate_id=inp.candidate.id,
            approval_decision_id=inp.approval.id,
            execution=execution,
            state=GhostWatchCampaignState.WAITING_FOR_EXTERNAL_DEPLOYMENT,
            approved_artifact_digest=inp.approved_artifact_digest,
            rollback_target=rollback_target,
            twin_prediction=TwinPredictionV1(
                promotion_candidate_id=inp.candidate.id,
                expected_artifact_digest=inp.approved_artifact_digest,
                expected_behavior_summary="Auth bypass blocked; proxy header policy enforced",
            ),
        )
        self._campaigns[camp.id] = camp
        self._evidence[camp.id] = []
        self._surprises[camp.id] = []
        return camp

    def get(self, campaign_id: uuid.UUID) -> GhostWatchCampaignV1 | None:
        return self._campaigns.get(campaign_id)

    def observe_and_analyze(
        self,
        campaign_id: uuid.UUID,
        *,
        adapter: MockDeploymentExecutorAdapter,
        analysis: CanaryAnalysisV1,
    ) -> TickResult:
        camp = self._campaigns[campaign_id]
        events = ["deployment.observed", "canary.analysis_completed"]
        obs = adapter.observe_state()
        conf = compare_deployment(
            camp.approved_artifact_digest,
            obs,
            approved_config_fingerprint="fp:ghostgate-approved",
        )
        camp.conformance = conf
        camp.execution.current_stage = adapter.observe_stage()
        camp.execution.status = DeploymentExecutionStatus.RUNNING
        camp.current_analysis = analysis
        events.append("deployment.conformance_checked")
        if conf.status.value == "MATERIAL_DIFFERENCE":
            events.append("deployment.variance_detected")
            camp.state = GhostWatchCampaignState.HOLD
            return TickResult(state=camp.state, events=events)

        outcome = analysis.outcome.value
        if outcome == "ADVANCE":
            camp.state = GhostWatchCampaignState.ADVANCE_RECOMMENDED
            events.append("rollout.advance_recommended")
        elif outcome == "HOLD":
            camp.state = GhostWatchCampaignState.HOLD
            events.append("rollout.hold")
        elif outcome == "ROLLBACK_RECOMMENDED":
            camp.state = GhostWatchCampaignState.ROLLBACK_RECOMMENDED
            events.append("rollout.rollback_recommended")

        ev = ProductionEvidenceV1(
            kind="metric_summary",
            content_hash=hashlib.sha256(outcome.encode()).hexdigest(),
            redacted_summary=f"stage={analysis.stage.value} outcome={outcome}",
        )
        self._evidence[campaign_id].append(ev)
        camp.evidence_ids.append(ev.id)
        events.append("production.evidence_created")

        surprise = detect_surprise(
            twin_expectation="auth bypass blocked in twin",
            production_observation=f"digest={obs.artifact_digest} stage={analysis.stage.value}",
            analysis_outcome=outcome,
        )
        if surprise:
            self._surprises[campaign_id].append(surprise)
            events.append("production.surprise_detected")

        return TickResult(state=camp.state, events=events)

    def maybe_invoke_rollback(
        self,
        campaign_id: uuid.UUID,
        *,
        adapter: MockDeploymentExecutorAdapter,
        target_digest: str,
    ) -> TickResult:
        camp = self._campaigns[campaign_id]
        events: list[str] = []
        if not may_request_control(
            camp.execution.authority_mode,
            ExecutorCapability.REQUEST_ROLLBACK,
        ):
            events.append("rollback.recommend_only")
            return TickResult(state=camp.state, events=events)

        if not camp.rollback_target or target_digest != camp.rollback_target.artifact_digest:
            camp.state = GhostWatchCampaignState.CRITICAL
            events.append("rollback.failed")
            return TickResult(state=camp.state, events=events)

        events.append("rollback.requested")
        camp.state = GhostWatchCampaignState.ROLLBACK_REQUESTED
        ok = adapter.request_rollback(target_digest=target_digest)
        if not ok:
            camp.state = GhostWatchCampaignState.CRITICAL
            events.append("rollback.failed")
            return TickResult(state=camp.state, events=events)

        camp.state = GhostWatchCampaignState.ROLLBACK_VERIFYING
        events.append("rollback.observed")
        obs_after = adapter.observe_state()
        verify_conf = compare_deployment(
            camp.rollback_target.artifact_digest if camp.rollback_target else "",
            obs_after,
            approved_config_fingerprint=adapter.config_fingerprint,
        )
        if verify_conf.status in (ConformanceStatus.MATCH, ConformanceStatus.FUNCTIONALLY_EQUIVALENT):
            camp.state = GhostWatchCampaignState.COMPLETED
            events.append("rollback.verified")
        else:
            camp.state = GhostWatchCampaignState.CRITICAL
            events.append("rollback.failed")
        return TickResult(state=camp.state, events=events)

    def attestation(self, campaign_id: uuid.UUID) -> DeploymentObservationAttestationV1:
        camp = self._campaigns[campaign_id]
        obs_digest = camp.conformance.observed_artifact_digest if camp.conformance else ""
        return DeploymentObservationAttestationV1(
            approved_change_hash=camp.execution.approved_change_hash,
            observed_artifact_digest=obs_digest,
            campaign_id=campaign_id,
        )

    def surprises(self, campaign_id: uuid.UUID) -> list[ProductionSurpriseV1]:
        return self._surprises.get(campaign_id, [])

    def ingest_external(
        self,
        campaign_id: uuid.UUID,
        record,
    ) -> TickResult:
        from .ingest import apply_external_record, verify_external_record

        camp = self._campaigns.get(campaign_id)
        if not camp:
            raise KeyError(campaign_id)
        verify_external_record(
            record,
            expected_change_hash=camp.execution.approved_change_hash,
            expected_campaign_id=campaign_id,
        )
        seen = self._seen_external_events.setdefault(campaign_id, set())
        camp, events = apply_external_record(camp, record, seen_events=seen)
        self._campaigns[campaign_id] = camp
        return TickResult(state=camp.state, events=events)
