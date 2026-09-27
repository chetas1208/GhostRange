"""Production surprise — twin vs production observation."""

from __future__ import annotations

from ghostrange_contracts.ghostwatch_m12 import ProductionSurpriseV1


def detect_surprise(
    *,
    twin_expectation: str,
    production_observation: str,
    analysis_outcome: str,
) -> ProductionSurpriseV1 | None:
    if analysis_outcome in ("ROLLBACK_RECOMMENDED", "HOLD") and "digest=sha256:auth-v2.7" in production_observation:
        return ProductionSurpriseV1(
            description="Production behavior diverged from twin prediction during rollout",
            twin_expectation=twin_expectation,
            production_observation=production_observation,
            severity="MEDIUM",
        )
    return None
