import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from ghostrange_api.config import Settings
from ghostrange_api.main import create_app


@pytest.mark.asyncio
async def test_reconciliation_route_honest_provider_unavailable():
    app = create_app(Settings.from_env())
    rid = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/v1/ranges/{rid}/cost/reconciliation")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("PROVIDER_UNAVAILABLE", "PENDING", "MATCHED", "DIFFERENCE", "NOT_SUPPORTED")
        assert body["calculated_usd_micros"] >= 0
