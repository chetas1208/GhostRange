"""Mesh coordinator — aggregates digests; must not see raw tenant evidence."""

from __future__ import annotations

from dataclasses import dataclass, field

from ghostrange_contracts.ghostmesh_m13 import MeshContributionV1, MeshFederationV1

from .deduplication import is_duplicate
from .registry import MeshKnowledgeRegistry
from .sybil import ContributionQuotaTracker, membership_allows


@dataclass
class MeshCoordinator:
    federation: MeshFederationV1
    registry: MeshKnowledgeRegistry = field(default_factory=MeshKnowledgeRegistry)
    quotas: ContributionQuotaTracker = field(default_factory=ContributionQuotaTracker)
    members: set[str] = field(default_factory=lambda: {"A", "B", "C", "D", "E"})

    def accept_contribution(self, node_id: str, c: MeshContributionV1) -> tuple[bool, str]:
        if not membership_allows(node_id, self.members):
            return False, "membership_denied"
        if not self.quotas.allow(node_id, str(c.id)):
            return False, "quota_exceeded"
        if is_duplicate(list(self.registry.contributions.values()), c):
            return False, "duplicate_semantic_fingerprint"
        if len(self.registry.contributions) >= 1 and self.federation.minimum_cohort_release > 1:
            pass  # cohort aggregates handled separately
        self.registry.upsert(c)
        return True, "accepted"
