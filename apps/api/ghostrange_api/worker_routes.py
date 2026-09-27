from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response

from .worker_models import (
    WorkerHeartbeatRequest,
    WorkerRegisterRequest,
    WorkerTaskCompleteRequest,
    WorkerTaskFailRequest,
)

router = APIRouter(prefix="/v1/workers", tags=["workers"])

_AGENT = Path(__file__).resolve().parents[3] / "deploy/worker/worker_agent.py"


def _store(request: Request):
    store = getattr(request.app.state, "worker_store", None)
    if store is None:
        raise HTTPException(503, "worker store unavailable")
    return store


async def _worker_auth(
    request: Request,
    worker_id: uuid.UUID,
    authorization: str | None = Header(default=None),
) -> uuid.UUID:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    store = _store(request)
    try:
        await store.worker_from_token(worker_id, token)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    return worker_id


@router.get("/bootstrap/agent.py")
async def bootstrap_agent():
    if not _AGENT.is_file():
        raise HTTPException(404, "agent bundle missing")
    return PlainTextResponse(_AGENT.read_text(), media_type="text/plain")


@router.post("/register")
async def register_worker(request: Request, body: WorkerRegisterRequest):
    store = _store(request)
    try:
        worker_id, worker_token = await store.register_worker(
            bootstrap_token=body.bootstrap_token,
            provider_instance_id=body.provider_instance_id,
            capabilities=body.capabilities,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    return {"worker_id": str(worker_id), "worker_token": worker_token}


@router.post("/{worker_id}/heartbeat")
async def heartbeat(
    request: Request,
    worker_id: uuid.UUID,
    body: WorkerHeartbeatRequest,
    _auth: uuid.UUID = Depends(_worker_auth),
):
    store = _store(request)
    await store.heartbeat(worker_id, status=body.status, task_id=body.current_task_id)
    return {"ok": True}


@router.post("/{worker_id}/lease")
async def lease_task(request: Request, worker_id: uuid.UUID, _auth: uuid.UUID = Depends(_worker_auth)):
    store = _store(request)
    task = await store.lease_next_task(worker_id)
    if task is None:
        return Response(status_code=204)
    return task


@router.post("/{worker_id}/tasks/{task_id}/complete")
async def complete_task(
    request: Request,
    worker_id: uuid.UUID,
    task_id: uuid.UUID,
    body: WorkerTaskCompleteRequest,
    _auth: uuid.UUID = Depends(_worker_auth),
):
    store = _store(request)
    registry = getattr(request.app.state, "artifact_registry", None)
    artifact_id = None
    if registry is not None and body.artifact_bundle:
        payload = json.dumps(body.artifact_bundle, sort_keys=True).encode()
        sha = hashlib.sha256(payload).hexdigest()
        worker = await store.get_worker(worker_id)
        case_id = worker["range_id"] if worker else uuid.uuid4()
        rec = await registry.store_artifact(
            case_id=case_id,
            data=payload,
            mime_type="application/json",
            artifact_id=uuid.uuid4(),
        )
        artifact_id = rec.artifact_id
    await store.complete_task(worker_id, task_id, result=body.result, artifact_id=artifact_id)
    run = await store.get_worker(worker_id)
    if run:
        await store.set_run_status(run["run_id"], "COMPLETED")
    return {"ok": True, "artifact_id": str(artifact_id) if artifact_id else None}


@router.post("/{worker_id}/tasks/{task_id}/fail")
async def fail_task(
    request: Request,
    worker_id: uuid.UUID,
    task_id: uuid.UUID,
    body: WorkerTaskFailRequest,
    _auth: uuid.UUID = Depends(_worker_auth),
):
    store = _store(request)
    await store.fail_task(worker_id, task_id, body.reason)
    return {"ok": True}


@router.post("/{worker_id}/drain")
async def drain_worker(request: Request, worker_id: uuid.UUID, _auth: uuid.UUID = Depends(_worker_auth)):
    store = _store(request)
    await store.drain_worker(worker_id)
    return {"ok": True}
