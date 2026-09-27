"""M11 promotion API — no deploy."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from ghostrange_api.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_prepare_promotion(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/v1/promotion/prepare",
            json={"experiment_id": str(uuid.uuid4())},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["state"] in ("READY_FOR_REVIEW", "DRAFT", "REQUIRES_REVALIDATION")
    assert "APPROVED != DEPLOYED" in body["message"]
    cid = body["candidate_id"]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r2 = await client.get(f"/v1/promotion/candidates/{cid}")
    assert r2.status_code == 200
    assert r2.json()["patch_text"]


@pytest.mark.asyncio
async def test_stale_blocks_or_revalidates(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/v1/promotion/prepare",
            json={"experiment_id": str(uuid.uuid4()), "source_stale": True},
        )
    assert r.status_code == 200
    assert r.json()["state"] == "REQUIRES_REVALIDATION"
