import pytest
from httpx import ASGITransport, AsyncClient

from ghostrange_api.main import create_app


@pytest.mark.asyncio
async def test_simulate_rollout():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/v1/ghostwatch/simulate", json={"scenario": "good-canary"})
    assert r.status_code == 200
    body = r.json()
    assert body["label"] == "SIMULATED_ROLLOUT"
    assert len(body["steps"]) >= 1
