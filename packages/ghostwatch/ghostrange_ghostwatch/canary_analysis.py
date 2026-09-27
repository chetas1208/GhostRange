"""Deterministic multi-signal stage analysis."""

from __future__ import annotations

from ghostrange_contracts.ghostwatch_m12 import (
    CanaryAnalysisOutcome,
    CanaryAnalysisV1,
    ConformanceStatus,
    DeploymentConformanceReportV1,
    GateEvaluationStatus,
    RolloutStageKind,
)


def analyze_stage(
    stage: RolloutStageKind,
    *,
    conformance: DeploymentConformanceReportV1,
    health: GateEvaluationStatus,
    security: GateEvaluationStatus,
    error_rate: GateEvaluationStatus,
    latency: GateEvaluationStatus,
) -> CanaryAnalysisV1:
    gates = {
        "conformance": _conf_gate(conformance.status),
        "health": health,
        "security_invariant": security,
        "error_rate": error_rate,
        "latency": latency,
    }
    rationale: list[str] = []

    if gates["conformance"] == GateEvaluationStatus.FAIL:
        rationale.append("UNAPPROVED_DEPLOYMENT_VARIANCE")
        return CanaryAnalysisV1(
            stage=stage,
            outcome=CanaryAnalysisOutcome.HOLD,
            gate_results=gates,
            rationale_codes=rationale,
        )

    for name, status in gates.items():
        if status == GateEvaluationStatus.INSUFFICIENT_DATA:
            rationale.append("INSUFFICIENT_TELEMETRY")
            return CanaryAnalysisV1(
                stage=stage,
                outcome=CanaryAnalysisOutcome.HOLD,
                gate_results=gates,
                rationale_codes=rationale,
            )
        if status == GateEvaluationStatus.FAIL:
            rationale.append(f"{name.upper()}_FAIL")
            return CanaryAnalysisV1(
                stage=stage,
                outcome=CanaryAnalysisOutcome.ROLLBACK_RECOMMENDED,
                gate_results=gates,
                rationale_codes=rationale,
            )

    return CanaryAnalysisV1(
        stage=stage,
        outcome=CanaryAnalysisOutcome.ADVANCE,
        gate_results=gates,
        rationale_codes=["ALL_REQUIRED_GATES_PASS"],
    )


def _conf_gate(status: ConformanceStatus) -> GateEvaluationStatus:
    if status == ConformanceStatus.MATCH:
        return GateEvaluationStatus.PASS
    if status == ConformanceStatus.MATERIAL_DIFFERENCE:
        return GateEvaluationStatus.FAIL
    if status in (ConformanceStatus.UNKNOWN, ConformanceStatus.NOT_OBSERVABLE):
        return GateEvaluationStatus.INSUFFICIENT_DATA
    return GateEvaluationStatus.PASS
