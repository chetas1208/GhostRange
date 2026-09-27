"""GhostCostLedger with an in-memory core and optional Postgres snapshots.

The ledger remains process-local for mutation, while ``CostLedgerPersistence``
serializes and restores its state when the API is configured with durable
PostgreSQL. Provider invoice reconciliation is intentionally separate because
the current provider API does not expose invoice-level campaign totals.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from ghostrange_contracts.cost_v1 import (
    CampaignCostV1,
    CostCategory,
    CostConfidence,
    CostReservationV1,
    CostSemanticType,
    InferenceUsageRecordV1,
    ResourceCostRecordV1,
)
from ghostrange_cost.attribution import campaign_total_from_resources
from ghostrange_cost.compute_billing import accrue_running_resource_usd_micros, compute_ephemeral_cost_usd_micros
from ghostrange_cost.money import add_micros


@dataclass
class _ResourceEntry:
    record: ResourceCostRecordV1
    hourly_rate_usd_micros: int
    processed_event_ids: set[str] = field(default_factory=set)


class GhostCostLedger:
    def __init__(self) -> None:
        self._lock = RLock()
        self._resources: dict[str, _ResourceEntry] = {}
        self._inference: dict[str, InferenceUsageRecordV1] = {}
        self._reservations: dict[uuid.UUID, CostReservationV1] = {}
        self._campaign_id: str | None = None

    def bind_campaign(self, campaign_id: str) -> None:
        with self._lock:
            self._campaign_id = campaign_id

    def idempotent(self, resource_id: str, event_id: str) -> bool:
        ent = self._resources.get(resource_id)
        if ent is None:
            return False
        return event_id in ent.processed_event_ids

    def mark_event(self, resource_id: str, event_id: str) -> None:
        ent = self._resources.get(resource_id)
        if ent:
            ent.processed_event_ids.add(event_id)

    def register_resource(
        self,
        record: ResourceCostRecordV1,
        *,
        hourly_rate_usd_micros: int,
        event_id: str | None = None,
    ) -> None:
        with self._lock:
            if record.resource_id in self._resources and event_id:
                if event_id in self._resources[record.resource_id].processed_event_ids:
                    return
            self._resources[record.resource_id] = _ResourceEntry(
                record=record, hourly_rate_usd_micros=hourly_rate_usd_micros
            )
            if event_id:
                self._resources[record.resource_id].processed_event_ids.add(event_id)

    def update_resource_lifecycle(self, resource_id: str, **lifecycle_fields: Any) -> None:
        with self._lock:
            ent = self._resources.get(resource_id)
            if not ent:
                return
            lc = ent.record.lifecycle.model_copy(update=lifecycle_fields)
            ent.record = ent.record.model_copy(update={"lifecycle": lc})

    def refresh_resource_accrual(
        self,
        resource_id: str,
        *,
        provider_lifetime_seconds: int,
        as_of: datetime | None = None,
    ) -> None:
        _ = as_of
        with self._lock:
            ent = self._resources.get(resource_id)
            if not ent:
                return
            lc = ent.record.lifecycle
            accrued, state = accrue_running_resource_usd_micros(
                hourly_rate_usd_micros=ent.hourly_rate_usd_micros,
                provider_lifetime_seconds=provider_lifetime_seconds,
                destroy_requested=lc.destroy_requested_at is not None,
                provider_destroyed=lc.provider_destroyed_at is not None and lc.billing_end_confirmed,
            )
            ent.record = ent.record.model_copy(
                update={
                    "accrued_estimate_usd_micros": accrued,
                    "committed_usd_micros": max(ent.record.committed_usd_micros, accrued),
                    "billing_end_state": state,
                }
            )

    def finalize_resource(
        self,
        resource_id: str,
        *,
        provider_lifetime_seconds: int,
        hourly_rate_usd: str,
        event_id: str | None = None,
    ) -> None:
        with self._lock:
            ent = self._resources.get(resource_id)
            if ent and event_id and event_id in ent.processed_event_ids:
                return
            if ent:
                rate_str = f"{ent.hourly_rate_usd_micros / 1_000_000:.6f}"
            else:
                rate_str = hourly_rate_usd
            result = compute_ephemeral_cost_usd_micros(
                hourly_rate_usd=rate_str,
                provider_lifetime_seconds=provider_lifetime_seconds,
            )
            if not ent:
                return
            if ent:
                ent.record = ent.record.model_copy(
                    update={
                        "final_usd_micros": result.total_usd_micros,
                        "accrued_estimate_usd_micros": result.total_usd_micros,
                        "committed_usd_micros": result.total_usd_micros,
                        "billing_end_state": "FINALIZED",
                    }
                )
                lc = ent.record.lifecycle.model_copy(update={"billing_end_confirmed": True})
                ent.record = ent.record.model_copy(update={"lifecycle": lc})
                if event_id:
                    ent.processed_event_ids.add(event_id)

    def record_inference(self, usage: InferenceUsageRecordV1, *, event_id: str | None = None) -> None:
        with self._lock:
            if usage.request_id in self._inference:
                return
            self._inference[usage.request_id] = usage

    def reserve(self, reservation: CostReservationV1) -> bool:
        with self._lock:
            campaign = self.campaign_snapshot(reservation.campaign_id)
            outstanding = self._reserved_total_locked(reservation.campaign_id)
            if campaign.total_known_usd_micros + outstanding + reservation.reserved_usd_micros > self._budget_cap():
                return False
            self._reservations[reservation.reservation_id] = reservation
            return True

    def release_reservation(self, reservation_id: uuid.UUID) -> None:
        with self._lock:
            self._reservations.pop(reservation_id, None)

    def _budget_cap(self) -> int:
        # Conservative default; API injects real cap via configure_budget_cap
        return getattr(self, "_budget_cap_usd_micros", usd_to_micros_cap_default())

    def configure_budget_cap_usd_micros(self, cap: int) -> None:
        self._budget_cap_usd_micros = cap

    def _reserved_total_locked(self, campaign_id: str) -> int:
        return add_micros(*(r.reserved_usd_micros for r in self._reservations.values() if r.campaign_id == campaign_id))

    def export_state(self) -> dict[str, Any]:
        """Serialize ledger for Postgres persistence (restart recovery)."""
        with self._lock:
            resources = []
            for ent in self._resources.values():
                resources.append(
                    {
                        "record": ent.record.model_dump(mode="json"),
                        "hourly_rate_usd_micros": ent.hourly_rate_usd_micros,
                        "processed_event_ids": sorted(ent.processed_event_ids),
                    }
                )
            inference = [u.model_dump(mode="json") for u in self._inference.values()]
            reservations = [r.model_dump(mode="json") for r in self._reservations.values()]
            return {
                "campaign_id": self._campaign_id,
                "resources": resources,
                "inference": inference,
                "reservations": reservations,
                "budget_cap_usd_micros": getattr(self, "_budget_cap_usd_micros", None),
            }

    def import_state(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._resources.clear()
            self._inference.clear()
            self._reservations.clear()
            self._campaign_id = data.get("campaign_id")
            cap = data.get("budget_cap_usd_micros")
            if cap is not None:
                self._budget_cap_usd_micros = int(cap)
            for row in data.get("resources") or []:
                rec = ResourceCostRecordV1.model_validate(row["record"])
                ent = _ResourceEntry(
                    record=rec,
                    hourly_rate_usd_micros=int(row["hourly_rate_usd_micros"]),
                    processed_event_ids=set(row.get("processed_event_ids") or []),
                )
                self._resources[rec.resource_id] = ent
            for row in data.get("inference") or []:
                usage = InferenceUsageRecordV1.model_validate(row)
                self._inference[usage.request_id] = usage
            for row in data.get("reservations") or []:
                res = CostReservationV1.model_validate(row)
                self._reservations[res.reservation_id] = res

    def campaign_snapshot(self, campaign_id: str) -> CampaignCostV1:
        with self._lock:
            compute_micros = campaign_total_from_resources(
                [e.record.final_usd_micros or e.record.accrued_estimate_usd_micros for e in self._resources.values()]
            )
            infer_micros = add_micros(
                *(u.calculated_usd_micros or 0 for u in self._inference.values() if u.calculated_usd_micros)
            )
            categories = {
                CostCategory.COMPUTE_EPHEMERAL.value: compute_micros,
                CostCategory.INFERENCE.value: infer_micros,
            }
            unknown: list[str] = []
            if not self._resources and not self._inference:
                unknown.append("no metered resources yet")
            total = add_micros(compute_micros, infer_micros)
            return CampaignCostV1(
                campaign_id=campaign_id,
                semantic_type=CostSemanticType.ACCRUED_ESTIMATE,
                confidence=CostConfidence.PARTIAL if unknown else CostConfidence.ESTIMATED_FROM_PROVIDER_POLICY,
                categories=categories,
                unknown_components=unknown,
                total_known_usd_micros=total,
                total_projected_usd_micros=total,
                finalized=False,
            )


def usd_to_micros_cap_default() -> int:
    from ghostrange_cost.money import usd_to_micros

    return usd_to_micros("25")
