import pytest
from httpx import ASGITransport, AsyncClient

from ghostrange_api.main import create_app


@pytest.mark.asyncio
async def test_m20_golden_campaign_mock():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/campaigns/golden")
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign"]["phase"] in ("COMPLETED", "FAILED")
    assert body["report"]["hypothesis_count"] == 3
    assert body["arena_recommendation"] == "QUALIFIED"
    assert "evidence_bundle" in body
    assert body["owned_workers"] == []


@pytest.mark.asyncio
async def test_m20_legacy_golden_path_still_works():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/golden-path/runs")
    assert resp.status_code == 200
    assert "campaign_id" in resp.json()
