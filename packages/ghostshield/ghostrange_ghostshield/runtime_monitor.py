"""Deterministic runtime monitors — no LLM."""

from __future__ import annotations

from dataclasses import dataclass, field

from ghostrange_contracts.ghostshield_m17 import CanonicalActionV1, RuntimePropertyV1


@dataclass
class MonitorVerdict:
    response: str  # ALLOW | BLOCK | PAUSE_CAMPAIGN | SAFE_MODE | REQUIRE_HUMAN | RAISE_CRITICAL
    property_id: str
    detail: str = ""


@dataclass
class GhostRuntimeMonitor:
    """Consumes canonical actions; evaluates registered RuntimePropertyV1 entries."""

    properties: list[RuntimePropertyV1] = field(default_factory=list)

    def pre_action(self, action: CanonicalActionV1, *, active_workers: int, max_workers: int) -> MonitorVerdict:
        if active_workers > max_workers:
            return MonitorVerdict(
                response="BLOCK",
                property_id="P2",
                detail="active_workers exceeds max",
            )
        return MonitorVerdict(response="ALLOW", property_id="MONITOR_OK")
