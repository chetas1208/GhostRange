"""Mock external deployment executor for tests and simulator."""

from __future__ import annotations

from dataclasses import dataclass, field

from ghostrange_contracts.ghostwatch_m12 import (
    DeploymentExecutorCapabilitiesV1,
    ExecutorCapability,
    ObservedDeploymentStateV1,
    RolloutStageKind,
)


@dataclass
class MockDeploymentExecutorAdapter:
    adapter_id: str = "mock-executor-v1"
    approved_digest: str = "sha256:auth-v2.7"
    rollback_digest: str = "sha256:auth-v2.6"
    current_digest: str = "sha256:auth-v2.6"
    config_fingerprint: str = "fp:ghostgate-approved"
    stage: RolloutStageKind = RolloutStageKind.PRE_DEPLOY
    traffic_new: float = 0.0
    rollback_invocations: list[str] = field(default_factory=list)
    capabilities: DeploymentExecutorCapabilitiesV1 = field(
        default_factory=lambda: DeploymentExecutorCapabilitiesV1(
            adapter_id="mock-executor-v1",
            capabilities=[
                ExecutorCapability.OBSERVE_STATUS,
                ExecutorCapability.OBSERVE_REVISION,
                ExecutorCapability.OBSERVE_STAGE,
                ExecutorCapability.REQUEST_PAUSE,
                ExecutorCapability.REQUEST_ROLLBACK,
            ],
            environment_label="SIMULATED_ROLLOUT",
        )
    )

    def observe_state(self) -> ObservedDeploymentStateV1:
        return ObservedDeploymentStateV1(
            artifact_digest=self.current_digest,
            config_fingerprint=self.config_fingerprint,
            service_version="auth-v2.7" if self.current_digest == self.approved_digest else "auth-v2.6",
            deployment_revision=self.current_digest,
            traffic_percentage_new=self.traffic_new,
            source=self.adapter_id,
        )

    def observe_stage(self) -> RolloutStageKind:
        return self.stage

    def request_pause(self) -> bool:
        self.stage = RolloutStageKind.HOLD
        return True

    def request_rollback(self, *, target_digest: str) -> bool:
        if target_digest != self.rollback_digest:
            return False
        self.rollback_invocations.append(target_digest)
        self.current_digest = target_digest
        self.traffic_new = 0.0
        self.stage = RolloutStageKind.ROLLBACK
        return True

    def request_promotion(self) -> bool:
        return False
