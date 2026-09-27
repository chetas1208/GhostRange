"""Liveness/readiness and deployment metadata."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def health_live(request: Request):
    settings = request.app.state.settings
    return {
        "ok": True,
        "deploy_sha": settings.deploy_sha,
        "live_provider": settings.live_provider,
    }


@router.get("/health/ready")
async def health_ready(request: Request):
    settings = request.app.state.settings
    checks: dict[str, object] = {"postgres": "skipped", "redis": "skipped", "object_storage": "skipped", "inference": "skipped"}
    ok = True

    store = getattr(request.app.state, "postgres_store", None)
    if settings.use_postgres:
        if store is None:
            checks["postgres"] = "not_configured"
            ok = False
        else:
            try:
                async with store._pool.connection() as conn:  # noqa: SLF001
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT 1")
                checks["postgres"] = "ok"
            except Exception as exc:
                checks["postgres"] = f"error:{type(exc).__name__}"
                ok = False
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(settings.redis_url or "", socket_connect_timeout=3)
            await client.ping()
            await client.aclose()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error:{type(exc).__name__}"
            ok = False
    else:
        checks["postgres"] = "memory_mode"
        checks["redis"] = "memory_mode"
        if settings.require_durable:
            ok = False

    if settings.s3_configured:
        from .ops_routes import object_store_from_settings

        try:
            store_s3 = object_store_from_settings(settings)
            # Auth + endpoint check without mutating bucket on every probe.
            store_s3.exists("0" * 64)
            checks["object_storage"] = "ok"
        except Exception as exc:
            checks["object_storage"] = f"error:{type(exc).__name__}"
            ok = False

    if settings.inference_configured:
        from .ops_routes import inference_smoke

        result = await inference_smoke(settings, minimal=True)
        checks["inference"] = "ok" if result.get("ok") else result.get("status", "degraded")
        if not result.get("ok"):
            # Inference degraded does not fail readiness.
            checks["inference_degraded"] = True
    else:
        checks["inference"] = "not_configured"

    # Provider-agnostic model-assisted-inference surface: reflects whichever provider is
    # actually active for EITHER seam (the pre-existing Vultr path by default for free-text
    # generation, or the default-on local Laya classifier for structured
    # classification/extraction — see inference_router.py). Never fails readiness: an
    # offline/degraded intelligence provider is informational, same as the legacy
    # `inference` check above — GhostRange's core paths do not depend on it.
    inference_router = getattr(request.app.state, "inference_router", None)
    if inference_router is None:
        from .inference_router import build_inference_router

        inference_router = build_inference_router(settings)
    if inference_router.available or inference_router.classification_available:
        health = await inference_router.health()
        checks["intelligence"] = {
            "provider": health.provider,
            "status": health.status.value,
            "device": health.device,
            "model": health.model,
            "latency_ms": health.latency_ms,
            "mode": health.mode,
        }
        if health.detail:
            checks["intelligence"]["detail"] = health.detail
    else:
        checks["intelligence"] = {
            "provider": "not_configured",
            "status": "NOT_CONFIGURED",
            "device": None,
            "model": None,
            "latency_ms": None,
            "mode": None,
        }

    body = {"ok": ok, "checks": checks, "deploy_sha": settings.deploy_sha}
    if not ok:
        return JSONResponse(status_code=503, content=body)
    return body


@router.get("/health/version")
async def health_version(request: Request):
    settings = request.app.state.settings
    return {
        "service": "ghostrange-api",
        "version": "0.1.0",
        "deploy_sha": settings.deploy_sha,
        "durable_events": settings.use_postgres,
        "object_storage": settings.object_storage_provider if settings.s3_configured else "local",
    }
