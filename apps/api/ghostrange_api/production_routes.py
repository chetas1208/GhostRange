"""Production persistence proofs (Postgres + Object Storage)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/production", tags=["production"])


class PersistenceProbe(BaseModel):
    note: str = Field(default="ghostrange persistence probe")


@router.post("/persistence/roundtrip")
async def persistence_roundtrip(request: Request, body: PersistenceProbe):
    store = getattr(request.app.state, "postgres_store", None)
    if store is None:
        raise HTTPException(503, "durable postgres not active")
    registry = getattr(request.app.state, "artifact_registry", None)
    if registry is None:
        raise HTTPException(503, "artifact registry not configured")

    case_id = uuid.uuid4()
    payload = body.note.encode()
    created = await registry.store_artifact(case_id=case_id, data=payload, mime_type="text/plain")
    read_back, bytes_back = await registry.get_artifact(created.artifact_id)
    updated = await registry.update_artifact(
        created.artifact_id, (body.note + " updated").encode(), mime_type="text/plain"
    )
    _, final_bytes = await registry.get_artifact(updated.artifact_id)

    async with store._pool.connection() as conn:  # noqa: SLF001
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM artifact_registry WHERE case_id = %(case)s", {"case": case_id})
            count_row = await cur.fetchone()
    pg_count = int(count_row[0]) if count_row else 0

    return {
        "ok": True,
        "postgres": "read_write_ok",
        "artifact_id": str(created.artifact_id),
        "sha256": read_back.sha256,
        "size_bytes": len(bytes_back),
        "updated_size": len(final_bytes),
        "object_key": read_back.object_key,
        "postgres_rows_for_case": pg_count,
    }


@router.get("/dependencies")
async def dependency_matrix(request: Request):
    settings = request.app.state.settings
    return {
        "app_env": settings.app_env,
        "postgres_durable": settings.use_postgres,
        "object_storage": settings.s3_configured,
        "inference": settings.inference_configured,
        "scheduler_live": settings.scheduler_live,
        "max_active_workers": settings.max_active_workers,
    }
