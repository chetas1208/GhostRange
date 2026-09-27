"""Rollback plans and in-range simulation status."""

from __future__ import annotations

from ghostrange_contracts.ghostgate_m11 import RollbackPlanV1, RollbackStatus


def default_rollback_plan() -> RollbackPlanV1:
    return RollbackPlanV1(
        rollback_type="CONFIG_REVERT",
        steps=[
            "Restore prior auth middleware configuration",
            "Remove trusted proxy allowlist file",
            "Run post-rollback health checks",
        ],
        required_artifacts=["previous_config_snapshot", "compose.override.backup"],
        estimated_duration_minutes=10,
        data_reversibility="FULL",
        verification=["baseline auth behavior restored", "no header bypass"],
        limitations=[],
    )


def simulate_rollback_in_range(*, inject_failure: bool = False) -> RollbackStatus:
    """Disposable-world rollback drill (no production)."""
    if inject_failure:
        return RollbackStatus.TESTED_FAIL
    return RollbackStatus.TESTED_PASS
