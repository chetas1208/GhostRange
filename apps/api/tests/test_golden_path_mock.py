import uuid

import httpx
import pytest

from ghostrange_api.config import Settings
from ghostrange_api.golden_path import GoldenPathOrchestrator
from ghostrange_api.main import create_app


def test_golden_path_orchestrator_mock():
    root = Settings.from_env().repo_root
    result = GoldenPathOrchestrator(repo_root=root, live=False).run()
    assert result.scenario == "tenant_escalation"
    assert result.benchmark.bundle_verified is True
    assert "director:" in " ".join(result.phases)
    assert "adversarial:" in " ".join(result.phases)
    assert "ledger:verified=True" in " ".join(result.phases)
    assert result.benchmark.scheduler_task_count > 0
    assert result.benchmark.scheduler_backlog == 0
    assert result.benchmark.worker_tasks_placed == result.benchmark.scheduler_ready_count
    assert "worker_orchestration:" in " ".join(result.phases)
    assert result.benchmark.live_mode == "mock"


def test_original_auth_incident_remains_selectable():
    root = Settings.from_env().repo_root
    result = GoldenPathOrchestrator(repo_root=root, live=False, scenario="auth_incident").run()
    assert result.scenario == "auth_incident"
    assert result.benchmark.bundle_verified is True
    assert result.benchmark.scheduler_backlog == 0


@pytest.mark.asyncio
async def test_golden_path_api_endpoint():
    app = create_app(Settings.from_env())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/golden-path/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["benchmark"]["bundle_verified"] is True
        assert body["scenario"] == "tenant_escalation"
        assert body["benchmark"]["scheduler_backlog"] == 0
        assert len(body["phases"]) >= 4
        rid = body["range_id"]
        snap = await client.get(f"/v1/ranges/{rid}/snapshot")
        names = {e.get("event_name") for e in snap.json().get("events", [])}
        assert "golden_path.phase" in names
        assert "director.decision" in names


@pytest.mark.asyncio
async def test_scheduler_plan_preview():
    app = create_app(Settings.from_env())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        rid = uuid.uuid4()
        resp = await client.post(f"/v1/scheduler/plan-preview?range_id={rid}")
        assert resp.status_code == 200
        assert "action_count" in resp.json()


@pytest.mark.asyncio
async def test_multiverse_fork_events():
    app = create_app(Settings.from_env())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        rid = uuid.uuid4()
        resp = await client.post(f"/v1/ranges/{rid}/forks/multiverse?branches=3")
        assert resp.status_code == 200
        snap = await client.get(f"/v1/ranges/{rid}/snapshot")
        names = {e.get("event_name") for e in snap.json().get("events", [])}
        assert "world.fork.created" in names


def test_live_guard_without_flag():
    from ghostrange_api.golden_path import assert_live_allowed
    import os

    old = os.environ.get("GHOSTRANGE_LIVE")
    os.environ.pop("GHOSTRANGE_LIVE", None)
    try:
        with pytest.raises(RuntimeError, match="GHOSTRANGE_LIVE"):
            assert_live_allowed()
    finally:
        if old:
            os.environ["GHOSTRANGE_LIVE"] = old


def test_live_m20_path_delegates_teardown_without_false_failure():
    root = Settings.from_env().repo_root
    result = GoldenPathOrchestrator(
        repo_root=root,
        live=True,
        coordinated_live_teardown=True,
    ).run()

    assert "teardown:delegated_to_m20_live_worker" in result.phases
    assert "live teardown must use coordinated lease + vultr-control" not in result.errors
