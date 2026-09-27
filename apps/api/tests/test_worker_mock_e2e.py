"""Mock worker runtime E2E (requires Postgres + Redis from env)."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from ghostrange_api.config import Settings
from ghostrange_api.main import create_app


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL") or not os.environ.get("REDIS_URL"),
    reason="DATABASE_URL and REDIS_URL required",
)
def test_worker_benchmark_mock_runtime_e2e():
    settings = Settings.from_env()
    app = create_app(settings)
    with TestClient(app) as client:
        before = client.get("/v1/scheduler/compute-dry-check").json()
        assert before["owned_worker_count"] == 0
        rid = str(uuid.uuid4())
        resp = client.post(f"/v1/scheduler/worker-benchmark?range_id={rid}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body.get("task_completed") is True
        assert body.get("evidence_artifact_id") or body.get("benchmark")
        after = client.get("/v1/scheduler/compute-dry-check").json()
        assert after["owned_worker_count"] == 0
