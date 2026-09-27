"""Operator-only smoke endpoints (no secrets in responses)."""

from __future__ import annotations

import hashlib
import time
import uuid

import httpx
from fastapi import APIRouter, HTTPException, Request

from ghostrange_evidence.object_store import VultrObjectStorageStore

from .config import Settings

router = APIRouter(prefix="/v1/ops", tags=["ops"])


def object_store_from_settings(settings: Settings) -> VultrObjectStorageStore:
    if not settings.s3_configured:
        raise HTTPException(503, "object storage not configured")
    return VultrObjectStorageStore(
        settings.s3_bucket or "",
        endpoint_url=settings.s3_endpoint or "",
        access_key=settings.s3_access_key_id,
        secret_key=settings.s3_secret_access_key,
        key_prefix=settings.s3_key_prefix,
    )


async def inference_smoke(settings: Settings, *, minimal: bool = False) -> dict:
    if not settings.inference_configured:
        return {"ok": False, "status": "not_configured"}
    url = settings.inference_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.inference_api_key}"}
    payload = {
        "model": settings.inference_model,
        "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
        "max_tokens": 8 if minimal else 16,
    }
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        latency_ms = int((time.perf_counter() - started) * 1000)
        ok = resp.status_code < 400
        return {
            "ok": ok,
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
            "model": settings.inference_model,
        }
    except Exception as exc:
        return {"ok": False, "status": type(exc).__name__}


@router.post("/smoke/object-storage")
async def smoke_object_storage(request: Request):
    settings: Settings = request.app.state.settings
    store = object_store_from_settings(settings)
    data = f"ghostrange-smoke-{uuid.uuid4()}".encode()
    key = hashlib.sha256(data).hexdigest()
    store.put(key, data)
    got = store.get(key)
    if got != data:
        raise HTTPException(500, "object storage roundtrip failed")
    return {"ok": True, "key_prefix": settings.s3_key_prefix, "bytes": len(data)}


@router.post("/smoke/inference")
async def smoke_inference_route(request: Request):
    settings: Settings = request.app.state.settings
    result = await inference_smoke(settings, minimal=False)
    if not result.get("ok"):
        raise HTTPException(502, result)
    return result
