"""Bridge compute lifecycle → GhostCostLedger + SSE cost.snapshot.updated."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ghostrange_contracts.cost_v1 import ResourceCostRecordV1, ResourceLifecycleTimestampsV1
from ghostrange_cost.ledger import GhostCostLedger
from ghostrange_cost.money import format_usd_display, usd_to_micros

from .memory_events import MemoryEventGateway


class CostAccountingBridge:
    def __init__(self, ledger: GhostCostLedger, *, persist: Any | None = None) -> None:
        self._ledger = ledger
        self._persist = persist
        self._resource_started: dict[str, datetime] = {}

    async def emit_snapshot(
        self,
        gateway: MemoryEventGateway,
        range_id: uuid.UUID,
        *,
        campaign_id: str | None = None,
    ) -> None:
        cid = campaign_id or str(range_id)
        snap = self._ledger.campaign_snapshot(cid)
        payload: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_name": "cost.snapshot.updated",
            "schema_version": "1",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "campaign_id": cid,
            "semantic_type": snap.semantic_type.value,
            "confidence": snap.confidence.value,
            "total_known_usd_micros": snap.total_known_usd_micros,
            "unknown_components": snap.unknown_components,
            "finalized": snap.finalized,
            "categories": snap.categories,
            "display_known_total": format_usd_display(snap.total_known_usd_micros),
        }
        await gateway.append_legacy(range_id, payload, source="cost-bridge")
        if self._persist is not None:
            await self._persist.save_campaign(cid, self._ledger)

    async def on_compute_ready(
        self,
        gateway: MemoryEventGateway,
        range_id: uuid.UUID,
        *,
        resource_id: str,
        hourly_rate_usd: float,
        event_id: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        self._resource_started[resource_id] = now
        rate_micros = usd_to_micros(f"{hourly_rate_usd:.6f}")
        ps = uuid.uuid4()
        rec = ResourceCostRecordV1(
            resource_id=resource_id,
            campaign_id=str(range_id),
            product="cloud_compute",
            price_snapshot_id=ps,
            lifecycle=ResourceLifecycleTimestampsV1(
                provider_created_at=now,
                ready_at=now,
            ),
        )
        self._ledger.register_resource(rec, hourly_rate_usd_micros=rate_micros, event_id=event_id)
        self._ledger.refresh_resource_accrual(resource_id, provider_lifetime_seconds=1)
        await self.emit_snapshot(gateway, range_id)

    async def on_compute_released(
        self,
        gateway: MemoryEventGateway,
        range_id: uuid.UUID,
        *,
        resource_id: str,
        hourly_rate_usd: float,
        event_id: str,
        legacy_total_usd: Optional[float] = None,
    ) -> None:
        started = self._resource_started.get(resource_id, datetime.now(timezone.utc))
        lifetime = max(1, int((datetime.now(timezone.utc) - started).total_seconds()))
        self._ledger.finalize_resource(
            resource_id,
            provider_lifetime_seconds=lifetime,
            hourly_rate_usd=f"{hourly_rate_usd:.6f}",
            event_id=event_id,
        )
        _ = legacy_total_usd
        await self.emit_snapshot(gateway, range_id)
