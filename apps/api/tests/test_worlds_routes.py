import pytest
from httpx import ASGITransport, AsyncClient

from ghostrange_api.main import create_app
from ghostrange_api.config import Settings


@pytest.mark.asyncio
async def test_worlds_list_requires_range_id():
    app = create_app(Settings.from_env())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/worlds")
        assert r.status_code == 200
        assert r.json()["worlds"] == []
