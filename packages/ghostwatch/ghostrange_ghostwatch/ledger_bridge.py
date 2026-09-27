"""GhostLedger rollout lineage — promotion + observation events (M11 blocker partial close)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromotionLineageEvent:
    event_name: str
    payload: dict[str, Any]
    source: str = "ghostwatch"


@dataclass
class InMemoryPromotionLedger:
    """Until full M7 live capture — durable enough for API/SSE wiring tests."""

    events: list[PromotionLineageEvent] = field(default_factory=list)

    def append(self, event_name: str, payload: dict[str, Any]) -> None:
        self.events.append(PromotionLineageEvent(event_name=event_name, payload=payload))

    def promotion_lineage_ok(self) -> bool:
        names = {e.event_name for e in self.events}
        return "promotion.bundle_created" in names or "ghostwatch.campaign_started" in names
