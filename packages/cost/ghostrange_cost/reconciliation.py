"""Compare calculated campaign cost vs provider-reported (never overwrite calculated)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ReconciliationStatus(str, Enum):
    PENDING = "PENDING"
    MATCHED = "MATCHED"
    DIFFERENCE = "DIFFERENCE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    NOT_SUPPORTED = "NOT_SUPPORTED"


@dataclass(frozen=True, slots=True)
class CostReconciliationV1:
    campaign_id: str
    calculated_usd_micros: int
    provider_reported_usd_micros: Optional[int]
    delta_usd_micros: Optional[int]
    status: ReconciliationStatus
    policy_snapshot: str
    note: str = ""

    def to_json(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "calculated_usd_micros": self.calculated_usd_micros,
            "provider_reported_usd_micros": self.provider_reported_usd_micros,
            "delta_usd_micros": self.delta_usd_micros,
            "status": self.status.value,
            "policy_snapshot": self.policy_snapshot,
            "note": self.note,
        }


def reconcile_campaign_cost(
    *,
    campaign_id: str,
    calculated_usd_micros: int,
    provider_reported_usd_micros: Optional[int],
    policy_snapshot: str = "vultr_one_hour_minimum_v1",
    tolerance_micros: int = 10_000,
) -> CostReconciliationV1:
    if provider_reported_usd_micros is None:
        return CostReconciliationV1(
            campaign_id=campaign_id,
            calculated_usd_micros=calculated_usd_micros,
            provider_reported_usd_micros=None,
            delta_usd_micros=None,
            status=ReconciliationStatus.PROVIDER_UNAVAILABLE,
            policy_snapshot=policy_snapshot,
            note="Vultr API does not expose invoice-level campaign totals; use CALCULATED as authoritative.",
        )
    delta = provider_reported_usd_micros - calculated_usd_micros
    status = (
        ReconciliationStatus.MATCHED
        if abs(delta) <= tolerance_micros
        else ReconciliationStatus.DIFFERENCE
    )
    return CostReconciliationV1(
        campaign_id=campaign_id,
        calculated_usd_micros=calculated_usd_micros,
        provider_reported_usd_micros=provider_reported_usd_micros,
        delta_usd_micros=delta,
        status=status,
        policy_snapshot=policy_snapshot,
    )
