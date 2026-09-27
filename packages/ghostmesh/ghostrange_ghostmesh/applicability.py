"""Match abstract remote patterns to local normalized graph — no remote topology."""

from __future__ import annotations

from ghostrange_contracts.ghostmesh_m13 import (
    ApplicabilityReportV1,
    ApplicabilityResult,
    LocalNormalizedGraphV1,
    MeshContributionV1,
)


def check_applicability(contribution: MeshContributionV1, local: LocalNormalizedGraphV1) -> ApplicabilityReportV1:
    tags = set(contribution.abstract_pattern.abstract_tags)
    local_tags = set(local.tags)
    matched = sorted(tags & local_tags)

    if "UNRELATED_ARCH" in local_tags:
        return ApplicabilityReportV1(
            contribution_id=contribution.id,
            result=ApplicabilityResult.NOT_APPLICABLE,
            matched_tags=matched,
            explanation="Local architecture family unrelated to pattern.",
        )

    required = {"SESSION_REFRESH", "CACHED_IDENTITY", "PRIVILEGED_ROUTE", "AUTHORIZATION"}
    if required.issubset(tags):
        if {"SESSION_REFRESH", "CACHED_IDENTITY", "PRIVILEGED_ROUTE"}.issubset(local_tags):
            return ApplicabilityReportV1(
                contribution_id=contribution.id,
                result=ApplicabilityResult.APPLICABLE,
                matched_tags=matched,
                explanation="Local graph contains cached identity, refresh path, and privileged authorization.",
            )
        if local_tags & {"SESSION_REFRESH", "CACHED_IDENTITY"}:
            return ApplicabilityReportV1(
                contribution_id=contribution.id,
                result=ApplicabilityResult.POSSIBLY_APPLICABLE,
                matched_tags=matched,
                explanation="Partial structural overlap — local experiment recommended.",
            )

    if "SUPERFICIAL_AUTH" in local_tags and "DECOY_MECHANISM" in local_tags:
        return ApplicabilityReportV1(
            contribution_id=contribution.id,
            result=ApplicabilityResult.POSSIBLY_APPLICABLE,
            matched_tags=matched,
            explanation="Superficial similarity; mechanism may differ (tenant C).",
        )

    if len(matched) >= 2:
        return ApplicabilityReportV1(
            contribution_id=contribution.id,
            result=ApplicabilityResult.POSSIBLY_APPLICABLE,
            matched_tags=matched,
            explanation="Partial tag overlap.",
        )

    return ApplicabilityReportV1(
        contribution_id=contribution.id,
        result=ApplicabilityResult.NOT_APPLICABLE,
        matched_tags=matched,
        explanation="Insufficient structural overlap.",
    )
