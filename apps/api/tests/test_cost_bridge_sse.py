import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from ghostrange_api.main import create_app
from ghostrange_api.config import Settings


@pytest.mark.asyncio
async def test_m2_run_emits_cost_snapshot_event():
    app = create_app(Settings.from_env())
    transport = ASGITransport(app=app)
    rid = uuid.uuid4()
    async with AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        await client.post(f"/v1/ranges/{rid}/runs/m2")
        for _ in range(80):
            snap = await client.get(f"/v1/ranges/{rid}/snapshot")
            events = snap.json().get("events") or []
            if any(e.get("event_name") == "cost.snapshot.updated" for e in events):
                break
            await asyncio.sleep(0.25)
        else:
            pytest.fail("cost.snapshot.updated not observed")
        cost = await client.get(f"/v1/ranges/{rid}/cost")
        assert cost.status_code == 200
        assert cost.json()["total_known_usd_micros"] >= 0
