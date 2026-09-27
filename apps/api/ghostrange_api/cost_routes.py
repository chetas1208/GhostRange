"""Canonical campaign/range cost — frontend must not reimplement billing."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ghostrange_cost.ledger import GhostCostLedger
from ghostrange_cost.money import format_usd_display

router = APIRouter(tags=["cost"])


def _ledger(request: Request) -> GhostCostLedger:
    ledger = getattr(request.app.state, "cost_ledger", None)
    if ledger is None:
        raise HTTPException(status_code=503, detail="cost ledger unavailable")
    return ledger


@router.get("/v1/ranges/{range_id}/cost")
async def range_cost(request: Request, range_id: str):
    snap = _ledger(request).campaign_snapshot(range_id)
    body = snap.model_dump(mode="json")
    body["display"] = {
        "semantic_type": snap.semantic_type.value,
        "known_total": format_usd_display(snap.total_known_usd_micros),
        "finalized": snap.finalized,
        "unknown_components": snap.unknown_components,
    }
    return body


@router.get("/v1/campaigns/{campaign_id}/cost")
async def campaign_cost(request: Request, campaign_id: str):
    return await range_cost(request, campaign_id)


@router.get("/v1/ranges/{range_id}/cost/reconciliation")
async def range_cost_reconciliation(request: Request, range_id: str):
    from ghostrange_cost.reconciliation import reconcile_campaign_cost

    snap = _ledger(request).campaign_snapshot(range_id)
    rec = reconcile_campaign_cost(
        campaign_id=range_id,
        calculated_usd_micros=snap.total_known_usd_micros,
        provider_reported_usd_micros=snap.total_provider_reported_usd_micros,
    )
    return rec.to_json()


@router.get("/v1/cost/prices/status")
async def price_status(request: Request):
    from ghostrange_cost.vultr_policy import DEFAULT_VULTR_POLICY

    policy = DEFAULT_VULTR_POLICY
    return {
        "pricing_version": policy.policy_version,
        "retrieved_at": policy.retrieved_at,
        "sources": list(policy.sources),
        "minimum_billing_unit_seconds": policy.minimum_billing_unit_seconds,
        "stopped_instance_billed_until_destroyed": policy.stopped_instance_billed_until_destroyed,
        "inference": {
            "model": "per-model snapshots required",
            "note": "Do not hardcode rates; bind InferencePriceSnapshotV1 per request",
        },
    }
