"""Multidimensional change risk — no single opaque score."""

from __future__ import annotations

from ghostrange_contracts.ghostgate_m11 import ChangeActionKind, ChangeActionV1, ChangeRiskProfileV1, RiskLevel


def assess_risk(actions: list[ChangeActionV1], affected: list[str]) -> ChangeRiskProfileV1:
    identity = any(a.kind == ChangeActionKind.IDENTITY_POLICY for a in actions)
    network = any(a.kind == ChangeActionKind.NETWORK_POLICY for a in actions)
    data = any(a.kind == ChangeActionKind.DATABASE_MIGRATION_REF for a in actions)
    return ChangeRiskProfileV1(
        blast_radius=RiskLevel.MEDIUM if len(affected) > 1 else RiskLevel.LOW,
        identity_impact=RiskLevel.HIGH if identity else RiskLevel.NONE,
        network_impact=RiskLevel.MEDIUM if network else RiskLevel.LOW,
        data_impact=RiskLevel.HIGH if data else RiskLevel.NONE,
        reversibility=RiskLevel.LOW if data else RiskLevel.MEDIUM,
        affected_component_ids=affected,
    )
