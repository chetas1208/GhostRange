"""Production authority boundaries — observation ≠ deployment admin."""

from __future__ import annotations

import os
from dataclasses import dataclass

from ghostrange_contracts.ghostgate_m11 import ApprovalDecisionKind, ApprovalDecisionV1
from ghostrange_contracts.ghostwatch_m12 import DeploymentAuthorityMode, ExecutorCapability


FORBIDDEN_ACTION_TYPES = frozenset(
    {
        "ArbitraryKubectlAction",
        "ArbitraryTerraformApply",
        "ArbitrarySSHAction",
        "ProductionShellAction",
    }
)


@dataclass(frozen=True)
class AuthorityViolation:
    code: str
    detail: str


def control_globally_disabled() -> bool:
    return os.environ.get("GHOSTWATCH_CONTROL_DISABLED", "").lower() in ("1", "true", "yes")


def assert_not_forbidden_action(action_type: str) -> None:
    if action_type in FORBIDDEN_ACTION_TYPES:
        raise PermissionError(f"Forbidden production action: {action_type}")


def may_request_control(
    mode: DeploymentAuthorityMode,
    capability: ExecutorCapability,
) -> bool:
    if control_globally_disabled():
        return False
    if mode == DeploymentAuthorityMode.OBSERVE_ONLY:
        return False
    if capability == ExecutorCapability.REQUEST_ROLLBACK:
        return mode == DeploymentAuthorityMode.PREAUTHORIZED_ROLLBACK
    if capability == ExecutorCapability.REQUEST_PAUSE:
        return mode in (
            DeploymentAuthorityMode.PREAUTHORIZED_PAUSE,
            DeploymentAuthorityMode.PREAUTHORIZED_ROLLBACK,
        )
    if capability == ExecutorCapability.REQUEST_PROMOTION:
        return mode == DeploymentAuthorityMode.RECOMMEND  # recommend only — adapter may ignore
    return mode != DeploymentAuthorityMode.OBSERVE_ONLY


def validate_approval_for_control(decision: ApprovalDecisionV1, expected_hash: str) -> None:
    if decision.decision != ApprovalDecisionKind.APPROVED:
        raise PermissionError("Control requires APPROVED decision")
    if decision.approver_kind not in ("HUMAN", "SERVICE"):
        raise PermissionError("Invalid approver kind")
    if decision.change_candidate_hash != expected_hash:
        raise PermissionError("Approval hash mismatch — stale or superseded")


def block_model_escalation(actor_kind: str) -> None:
    if actor_kind.upper() in ("MODEL", "LLM", "AGENT", "GHOSTDIRECTOR", "GHOSTSCHEDULER"):
        raise PermissionError("Models and autonomous agents cannot escalate deployment authority")
