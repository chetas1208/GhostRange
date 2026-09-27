import pytest
from httpx import ASGITransport, AsyncClient

from ghostrange_api.main import create_app
from ghostrange_api.config import Settings


@pytest.mark.asyncio
async def test_range_cost_endpoint():
    app = create_app(Settings.from_env())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/ranges/test-range/cost")
        assert r.status_code == 200
        body = r.json()
        assert body["semantic_type"] == "ACCRUED_ESTIMATE"
        assert "display" in body
        assert "known_total" in body["display"]


@pytest.mark.asyncio
async def test_price_status_documents_minimum_quantum():
    app = create_app(Settings.from_env())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/cost/prices/status")
        assert r.status_code == 200
        assert r.json()["minimum_billing_unit_seconds"] == 3600
