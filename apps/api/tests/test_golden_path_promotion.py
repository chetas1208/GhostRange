"""Golden path + GhostGate promotion chain."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from ghostrange_api.main import create_app


@pytest.mark.asyncio
async def test_golden_path_with_promotion():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/v1/golden-path/runs?with_promotion=true")
    assert r.status_code == 200
    body = r.json()
    assert body.get("bundle_digest")
    promo = body.get("promotion")
    assert promo
    assert promo["candidate_id"]
    assert promo["state"] in ("READY_FOR_REVIEW", "DRAFT", "REQUIRES_REVALIDATION")
    assert "APPROVED" not in promo["state"]
