"""ProductionRolloutSimulator — SIMULATED_ROLLOUT, not production."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from ghostrange_contracts.ghostwatch_m12 import (
    DeploymentAuthorityMode,
    GateEvaluationStatus,
    GhostWatchCampaignState,
    RolloutStageKind,
)

from .adapters.mock import MockDeploymentExecutorAdapter
from .campaign import GhostWatch, StartCampaignInput
from .canary_analysis import analyze_stage
from .conformance import compare_deployment
from ghostrange_contracts.ghostgate_m11 import ApprovalDecisionKind, ApprovalDecisionV1, ProductionChangeCandidateV1, PromotionState
class SimScenario(str, Enum):
    GOOD_CANARY = "good-canary"
    BAD_SECURITY = "bad-security"
    UNAPPROVED_ARTIFACT = "unapproved-artifact"
    MISSING_TELEMETRY = "missing-telemetry"
    ROLLBACK_FAILURE = "rollback-failure"


@dataclass
class SimStepResult:
    stage: RolloutStageKind
    campaign_state: GhostWatchCampaignState
    analysis_outcome: str
    events: list[str] = field(default_factory=list)


@dataclass
class ProductionRolloutSimulator:
    """Deterministic rollout with optional failure injection."""

    label: str = "SIMULATED_ROLLOUT"

    def run_scenario(
        self,
        scenario: SimScenario,
        *,
        authority: DeploymentAuthorityMode = DeploymentAuthorityMode.RECOMMEND,
    ) -> list[SimStepResult]:
        approved = "sha256:auth-v2.7"
        rollback = "sha256:auth-v2.6"
        adapter = MockDeploymentExecutorAdapter(
            approved_digest=approved,
            rollback_digest=rollback,
            current_digest=rollback,
        )
        candidate = ProductionChangeCandidateV1(
            remediation_id=uuid.uuid4(),
            source_revision_id=uuid.uuid4(),
            twin_revision_id=uuid.uuid4(),
            experiment_id=uuid.uuid4(),
            evidence_root_digest="sim",
            change_candidate_hash="simhash",
            state=PromotionState.APPROVED,
        )
        decision = ApprovalDecisionV1(
            request_id=uuid.uuid4(),
            change_candidate_hash="simhash",
            decision=ApprovalDecisionKind.APPROVED,
            approver_id="human-sim",
        )
        gw = GhostWatch()
        if scenario == SimScenario.ROLLBACK_FAILURE:
            authority = DeploymentAuthorityMode.PREAUTHORIZED_ROLLBACK
        camp = gw.start_campaign(
            StartCampaignInput(
                candidate=candidate,
                approval=decision,
                approved_artifact_digest=approved,
                rollback_target_digest=rollback,
                authority_mode=authority,
                adapter=adapter,
            )
        )
        stages = [
            (RolloutStageKind.CANARY_10, 10.0),
            (RolloutStageKind.CANARY_25, 25.0),
            (RolloutStageKind.CANARY_50, 50.0),
            (RolloutStageKind.FULL, 100.0),
        ]
        results: list[SimStepResult] = []
        security = GateEvaluationStatus.PASS
        error = GateEvaluationStatus.PASS
        latency = GateEvaluationStatus.PASS
        health = GateEvaluationStatus.PASS

        for stage_kind, pct in stages:
            adapter.stage = stage_kind
            if scenario == SimScenario.UNAPPROVED_ARTIFACT and stage_kind == RolloutStageKind.CANARY_10:
                adapter.current_digest = "sha256:evil"
            else:
                adapter.current_digest = approved
            adapter.traffic_new = pct

            if scenario == SimScenario.BAD_SECURITY and stage_kind == RolloutStageKind.CANARY_25:
                security = GateEvaluationStatus.FAIL
            if scenario == SimScenario.MISSING_TELEMETRY and stage_kind == RolloutStageKind.CANARY_25:
                health = GateEvaluationStatus.INSUFFICIENT_DATA
            if scenario == SimScenario.GOOD_CANARY:
                security = GateEvaluationStatus.PASS
                health = GateEvaluationStatus.PASS

            obs = adapter.observe_state()
            conf = compare_deployment(
                approved,
                obs,
                approved_config_fingerprint=adapter.config_fingerprint,
                approved_service_version="auth-v2.7",
            )
            analysis = analyze_stage(
                stage_kind,
                conformance=conf,
                health=health,
                security=security,
                error_rate=error,
                latency=latency,
            )
            tick = gw.observe_and_analyze(camp.id, adapter=adapter, analysis=analysis)
            results.append(
                SimStepResult(
                    stage=stage_kind,
                    campaign_state=tick.state,
                    analysis_outcome=analysis.outcome.value,
                    events=tick.events,
                )
            )
            if analysis.outcome.value in ("HOLD", "ROLLBACK_RECOMMENDED"):
                if scenario == SimScenario.ROLLBACK_FAILURE:
                    adapter.rollback_digest = "sha256:wrong"
                gw.maybe_invoke_rollback(camp.id, adapter=adapter, target_digest=rollback)
                break
        return results
