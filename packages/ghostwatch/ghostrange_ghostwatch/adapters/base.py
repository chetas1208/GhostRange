"""Deployment executor adapter protocol."""

from __future__ import annotations

from typing import Protocol

from ghostrange_contracts.ghostwatch_m12 import (
    DeploymentExecutorCapabilitiesV1,
    ObservedDeploymentStateV1,
    RolloutStageKind,
)


class DeploymentExecutorAdapter(Protocol):
    capabilities: DeploymentExecutorCapabilitiesV1

    def observe_state(self) -> ObservedDeploymentStateV1: ...

    def observe_stage(self) -> RolloutStageKind: ...

    def request_pause(self) -> bool: ...

    def request_rollback(self, *, target_digest: str) -> bool: ...

    def request_promotion(self) -> bool: ...
