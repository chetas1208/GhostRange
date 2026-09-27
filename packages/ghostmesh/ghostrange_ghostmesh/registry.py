"""Mesh knowledge registry — safe contributions only."""

from __future__ import annotations

from dataclasses import dataclass, field

from ghostrange_contracts.ghostmesh_m13 import (
    AggregatedKnowledgeV1,
    ContributionRevocationV1,
    KnowledgeClass,
    MeshContributionV1,
    RemoteKnowledgeStatus,
)


@dataclass
class MeshKnowledgeRegistry:
    contributions: dict[str, MeshContributionV1] = field(default_factory=dict)
    revocations: dict[str, ContributionRevocationV1] = field(default_factory=dict)
    quarantined: set[str] = field(default_factory=set)

    def upsert(self, c: MeshContributionV1) -> None:
        key = str(c.id)
        if key in self.quarantined:
            return
        if key in self.revocations:
            return
        self.contributions[key] = c

    def quarantine(self, contribution_id: str, reason: str = "") -> None:
        self.quarantined.add(contribution_id)
        self.contributions.pop(contribution_id, None)

    def revoke(self, rev: ContributionRevocationV1) -> None:
        cid = str(rev.contribution_id)
        self.revocations[cid] = rev
        self.contributions.pop(cid, None)

    def status(self, contribution_id: str) -> RemoteKnowledgeStatus:
        if contribution_id in self.quarantined:
            return RemoteKnowledgeStatus.QUARANTINED
        if contribution_id in self.revocations:
            return RemoteKnowledgeStatus.REVOKED
        if contribution_id in self.contributions:
            return RemoteKnowledgeStatus.ELIGIBLE
        return RemoteKnowledgeStatus.UNSEEN

    def aggregate_class(self, kclass: KnowledgeClass, *, min_cohort: int) -> AggregatedKnowledgeV1 | None:
        items = [c for c in self.contributions.values() if c.knowledge_class == kclass]
        if len(items) < min_cohort:
            return None
        tags: list[str] = []
        for c in items:
            tags.extend(c.abstract_pattern.abstract_tags)
        unique = sorted(set(tags))
        from ghostrange_contracts.ghostmesh_m13 import KnowledgeAbstractionV1

        return AggregatedKnowledgeV1(
            knowledge_class=kclass,
            abstract_summary=KnowledgeAbstractionV1(abstract_tags=unique[:8], notes="cohort aggregate"),
            contributor_cohort_size=len(items),
            cohort_bucket_label=f"{len(items)}+",
            validation_success_rate=0.0,
        )
