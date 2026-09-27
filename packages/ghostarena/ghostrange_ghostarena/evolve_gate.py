"""Wire M18 promotion to M19 independent release report."""

from __future__ import annotations

from ghostrange_contracts.ghostarena_m19 import GhostArenaReleaseReportV1, ReleaseRecommendation


class ArenaPromotionBlocked(Exception):
    def __init__(self, report: GhostArenaReleaseReportV1) -> None:
        self.report = report
        super().__init__(report.recommendation.value)


def require_arena_for_promotion(report: GhostArenaReleaseReportV1 | None) -> None:
    if report is None:
        raise ArenaPromotionBlocked(
            GhostArenaReleaseReportV1(
                baseline_version="unknown",
                candidate_version="unknown",
                recommendation=ReleaseRecommendation.INSUFFICIENT_EVIDENCE,
                sanitized_diagnostics=["Missing GhostArenaReleaseReportV1"],
            )
        )
    if not report.qualifies_promotion():
        raise ArenaPromotionBlocked(report)
