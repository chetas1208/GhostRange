import asyncio
import uuid

import httpx
import pytest

from ghostrange_api.config import Settings
from ghostrange_api.main import create_app


@pytest.fixture
def app():
    return create_app(Settings.from_env())


@pytest.mark.asyncio
async def test_mock_m2_pipeline_emits_live_events(app):
    range_id = uuid.uuid4()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/v1/ranges/{range_id}/runs/m2")
        assert resp.status_code == 200
        for _ in range(120):
            snap = await client.get(f"/v1/ranges/{range_id}/snapshot")
            body = snap.json()
            if body.get("sequence", 0) >= 15:
                names = {e.get("event_name") for e in body.get("events", [])}
                if "world.destroyed" in names:
                    break
            await asyncio.sleep(0.25)
        else:
            pytest.fail("pipeline did not reach world.destroyed in time")
        snap = await client.get(f"/v1/ranges/{range_id}/snapshot")
        events = snap.json()["events"]
        names = {e.get("event_name") for e in events}
        assert "world.provisioning" in names or "world.ready" in names
        assert "scheduler.decision" in names
        assert "evidence.created" in names or "evidence.artifact_created" in names
        assert "verification.passed" in names or "verification.started" in names
        assert "world.destroyed" in names
