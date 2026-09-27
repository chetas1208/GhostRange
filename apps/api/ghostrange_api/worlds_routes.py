"""World graph derived from event snapshot (no duplicate world DB)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["worlds"])


def _fold_worlds(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    worlds: dict[str, dict[str, Any]] = {}
    forks: list[dict[str, Any]] = []
    for ev in events:
        name = str(ev.get("event_name") or ev.get("type") or "")
        p = ev
        if name == "world.requested":
            wid = str(p.get("world_id"))
            worlds[wid] = {
                "id": wid,
                "range_id": str(p.get("range_id", "")),
                "parent_world_id": p.get("parent_world_id"),
                "status": "REQUESTED",
            }
        elif name in ("world.provisioning", "world.ready", "world.destroyed"):
            wid = str(p.get("world_id"))
            w = worlds.setdefault(wid, {"id": wid})
            w["status"] = name.split(".")[-1].upper()
        elif name == "world.fork.created":
            forks.append(
                {
                    "parent_world_id": str(p.get("parent_world_id", "")),
                    "child_world_id": str(p.get("child_world_id", "")),
                    "fork_reason": p.get("fork_reason") or p.get("branch_label"),
                }
            )
    return {"worlds": list(worlds.values()), "forks": forks}


@router.get("/v1/worlds")
async def list_worlds(request: Request, range_id: str | None = None):
    gw = request.app.state.gateway
    if range_id:
        try:
            rid = uuid.UUID(range_id)
        except ValueError as exc:
            raise HTTPException(400, "invalid range_id") from exc
        rows = await gw.replay(rid, 0)
        events = [r.to_client_event() for r in rows]
        folded = _fold_worlds(events)
        return {"range_id": range_id, **folded}
    return {"worlds": [], "forks": [], "note": "pass range_id query param"}


@router.get("/v1/worlds/{world_id}")
async def get_world(request: Request, world_id: str, range_id: str):
    try:
        rid = uuid.UUID(range_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid range_id") from exc
    gw = request.app.state.gateway
    rows = await gw.replay(rid, 0)
    events = [r.to_client_event() for r in rows]
    folded = _fold_worlds(events)
    for w in folded["worlds"]:
        if w["id"] == world_id:
            return w
    raise HTTPException(404, "world not found in range snapshot")
