"""Chain M10 golden path → M11 GhostGate (no production deploy)."""

from __future__ import annotations

import uuid
from typing import Any

from ghostrange_contracts._base import utc_now

from ghostrange_ghostgate.promote import GhostGate, PromotionPrepareInput

from .golden_path import GoldenPathResult


async def prepare_promotion_after_golden(
    gateway,
    result: GoldenPathResult,
    gate: GhostGate,
) -> dict[str, Any]:
    if not result.bundle_digest:
        raise ValueError("golden path missing bundle_digest — cannot bind promotion evidence")

    inp = PromotionPrepareInput(
        experiment_id=result.campaign_id,
        remediation_id=result.remediation_id or uuid.uuid5(result.campaign_id, "fix-b.2"),
        source_revision_id=result.source_revision_id or result.investigation_id,
        twin_revision_id=result.twin_revision_id or result.campaign_id,
        evidence_root_digest=result.bundle_digest,
        adversarial=result.adversarial_report,
        fidelity_ok=True,
    )
    promo = gate.prepare(inp)
    c = promo.candidate
    corr = result.benchmark.correlation_id
    for ev in promo.events:
        await gateway.append_legacy(
            result.range_id,
            {
                "event_name": ev,
                "schema_version": "1",
                "occurred_at": utc_now().isoformat(),
                "correlation_id": corr,
                "candidate_id": str(c.id),
                "state": c.state.value,
                "change_candidate_hash": c.change_candidate_hash,
            },
            source="ghostgate",
        )
    return {
        "candidate_id": str(c.id),
        "state": c.state.value,
        "change_candidate_hash": c.change_candidate_hash,
        "readiness_blockers": c.readiness.blockers,
        "events": promo.events,
    }
