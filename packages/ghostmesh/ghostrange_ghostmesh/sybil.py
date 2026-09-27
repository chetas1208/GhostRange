"""Agent 19 — Sybil resistance via membership + quotas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ContributionQuotaTracker:
    max_per_node_per_day: int = 10
    counts: dict[str, list[str]] = field(default_factory=dict)

    def allow(self, node_id: str, contribution_id: str) -> bool:
        today = datetime.now(timezone.utc).date().isoformat()
        key = f"{node_id}:{today}"
        bucket = self.counts.setdefault(key, [])
        if len(bucket) >= self.max_per_node_per_day:
            return False
        bucket.append(contribution_id)
        return True


def membership_allows(node_id: str, allowed_members: set[str]) -> bool:
    return node_id in allowed_members
