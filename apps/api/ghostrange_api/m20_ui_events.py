"""Durable SSE events for M20 UI acceptance (no frontend fixture injection)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from ghostrange_contracts._base import utc_now

from .multiverse_fork import emit_fork_events, fork_remediation_worlds

if TYPE_CHECKING:
    from .orchestrator import ActiveRun


async def emit_m20_ui_accent_events(gateway, run: ActiveRun, *, range_id: uuid.UUID) -> None:
    """Emit attack, fork, causal, shield deny, counterexample after world topology exists."""
    wid = run.world_id
    gw = str(uuid.uuid5(range_id, "gw01"))
    api = str(uuid.uuid5(range_id, "api01"))
    auth = str(uuid.uuid5(range_id, "auth01"))

    await gateway.append_legacy(
        range_id,
        {
            "event_name": "attack.observed",
            "schema_version": "1",
            "occurred_at": utc_now().isoformat(),
            "world_id": str(wid),
            "path": [gw, api, auth],
        },
        source="m20_ui",
        world_id=wid,
    )

    fork_result = fork_remediation_worlds(wid, count=3)
    await emit_fork_events(gateway, range_id, fork_result)

    await gateway.append_legacy(
        range_id,
        {
            "event_name": "causal.intervention_completed",
            "schema_version": "1",
            "occurred_at": utc_now().isoformat(),
            "world_id": str(wid),
            "label": "session_refresh_cache",
            "cache_blocks": True,
            "transport": "intervention-supported",
        },
        source="ghostcausal",
        world_id=wid,
    )
    await gateway.append_legacy(
        range_id,
        {
            "event_name": "causal.edge_supported",
            "schema_version": "1",
            "occurred_at": utc_now().isoformat(),
            "world_id": str(wid),
            "edge": "cache→stale_session",
            "support": "intervention-supported",
        },
        source="ghostcausal",
        world_id=wid,
    )
    await gateway.append_legacy(
        range_id,
        {
            "event_name": "causal.transport_rejected",
            "schema_version": "1",
            "occurred_at": utc_now().isoformat(),
            "world_id": str(wid),
            "reason": "negative_transfer_simulated",
            "simulated": True,
        },
        source="ghostcausal",
        world_id=wid,
    )

    await gateway.append_legacy(
        range_id,
        {
            "event_name": "execution.denied",
            "schema_version": "1",
            "occurred_at": utc_now().isoformat(),
            "world_id": str(wid),
            "action": "CREATE_SECOND_WORKER",
            "reason": "GHOSTRANGE_MAX_WORKERS=1",
            "policy": "GhostShield",
        },
        source="ghostshield",
        world_id=wid,
    )

    claim_id = str(uuid.uuid4())
    await gateway.append_legacy(
        range_id,
        {
            "event_name": "evidence.claim_updated",
            "schema_version": "1",
            "occurred_at": utc_now().isoformat(),
            "world_id": str(wid),
            "claim": {
                "id": claim_id,
                "world_id": str(wid),
                "statement": "Remediation Fix B eliminates stale session without cache flush",
                "anchored": False,
                "verified": False,
                "refuted": True,
            },
        },
        source="adversarial",
        world_id=wid,
    )
    await gateway.append_legacy(
        range_id,
        {
            "event_name": "adversarial.counterexample",
            "schema_version": "1",
            "occurred_at": utc_now().isoformat(),
            "world_id": str(wid),
            "claim_id": claim_id,
            "branch_label": "Fix B",
            "simulated": False,
        },
        source="adversarial",
        world_id=wid,
    )

    await gateway.append_legacy(
        range_id,
        {
            "event_name": "runtime.interruption",
            "schema_version": "1",
            "occurred_at": utc_now().isoformat(),
            "world_id": str(wid),
            "component": "auth_validate",
            "recovered": True,
            "simulated": True,
        },
        source="runtime",
        world_id=wid,
    )
    await gateway.append_legacy(
        range_id,
        {
            "event_name": "runtime.recovered",
            "schema_version": "1",
            "occurred_at": utc_now().isoformat(),
            "world_id": str(wid),
            "checkpoint_id": str(uuid.uuid4()),
        },
        source="runtime",
        world_id=wid,
    )


__all__ = ["emit_m20_ui_accent_events"]
