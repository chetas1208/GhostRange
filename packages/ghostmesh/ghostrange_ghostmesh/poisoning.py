"""Poisoning detection — quarantine suspicious contributions."""

from __future__ import annotations

from ghostrange_contracts.ghostmesh_m13 import ContributionAnomalyV1, MeshContributionV1

from .dlp import scan_contribution_payload


def detect_anomalies(contribution: MeshContributionV1) -> list[ContributionAnomalyV1]:
    anomalies: list[ContributionAnomalyV1] = []
    dlp = scan_contribution_payload(contribution.model_dump(mode="json"))
    if not dlp.ok:
        anomalies.append(
            ContributionAnomalyV1(
                contribution_id=contribution.id,
                anomaly_kind="DLP_VIOLATION",
                severity="HIGH",
                reason_codes=[f.kind for f in dlp.findings],
            )
        )
    if contribution.evidence_strength > 0.99 and contribution.local_validation_count < 1:
        anomalies.append(
            ContributionAnomalyV1(
                contribution_id=contribution.id,
                anomaly_kind="IMPLausible_strength",
                severity="MEDIUM",
                reason_codes=["high_strength_zero_validations"],
            )
        )
    tags = contribution.abstract_pattern.abstract_tags
    if any(t.lower().startswith("run_") for t in tags):
        anomalies.append(
            ContributionAnomalyV1(
                contribution_id=contribution.id,
                anomaly_kind="EXECUTION_SMUGGLE",
                severity="CRITICAL",
                reason_codes=["tag_smuggle"],
            )
        )
    return anomalies


def should_quarantine(contribution: MeshContributionV1) -> bool:
    return any(a.severity in ("HIGH", "CRITICAL") for a in detect_anomalies(contribution))
