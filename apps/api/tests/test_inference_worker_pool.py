"""Real Vultr Serverless Inference concurrency proof + hard cap enforcement.

Skipped unless VULTR_INFERENCE_API_KEY is set (these make real, billable — if tiny —
network calls to https://api.vultrinference.com). Unlike the Vultr Compute API, Serverless
Inference is not IP-allowlisted, so this passes from any environment with a valid key.
"""

from __future__ import annotations

import os

import pytest

from ghostrange_api.config import Settings
from ghostrange_api.inference_service import InferenceService
from ghostrange_api.inference_worker_pool import InferenceWorkerPool, InferenceWorkerTask
from ghostrange_contracts.ghostshield_m17 import GhostShieldMode
from ghostrange_ghostshield import GhostExecutionGateway

pytestmark = pytest.mark.skipif(
    not os.environ.get("VULTR_INFERENCE_API_KEY"),
    reason="VULTR_INFERENCE_API_KEY required for real Serverless Inference calls",
)

_SYSMSG = (
    "Return ONLY valid JSON with keys: ack (string), n (number). "
    "Set ack to the literal string ok and n to the number given in the user message."
)


def _pool(monkeypatch, *, max_active_workers: str = "10", max_usd: str = "25") -> InferenceWorkerPool:
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.setenv("MAX_ACTIVE_WORKERS", max_active_workers)
    monkeypatch.setenv("INFERENCE_WORKER_MAX_USD", max_usd)
    monkeypatch.setenv("GHOSTSHIELD_MODE", "ENFORCE")
    settings = Settings.from_env()
    gateway = GhostExecutionGateway(mode=GhostShieldMode.ENFORCE)
    return InferenceWorkerPool(settings, InferenceService(settings), gateway)


@pytest.mark.asyncio
async def test_ten_real_concurrent_dispatches_overlap_and_have_distinct_ids(monkeypatch):
    pool = _pool(monkeypatch)
    tasks = [
        InferenceWorkerTask(system=_SYSMSG, user=f"n={i}", max_tokens=40, label=f"worker-{i}")
        for i in range(10)
    ]
    result = await pool.dispatch_batch(tasks)

    assert result.dispatched == 10, result.results
    assert result.refused == 0
    # Real, distinct request IDs sent to Vultr — not the same call replayed.
    ids = [r.request_id for r in result.results]
    assert len(set(ids)) == 10

    # Real overlap proof: parse timestamps and confirm at least 5 windows intersect
    # (i.e. this was genuinely concurrent, not serialized one-at-a-time).
    from datetime import datetime

    windows = [
        (datetime.fromisoformat(r.started_at), datetime.fromisoformat(r.finished_at))
        for r in result.results
    ]
    earliest_start = min(w[0] for w in windows)
    latest_of_starts = max(w[0] for w in windows)
    # All 10 dispatches must have started within a tight window (proves fan-out, not a loop
    # that waits for each call before starting the next).
    assert (latest_of_starts - earliest_start).total_seconds() < 2.0

    overlapping = 0
    for i, (s1, f1) in enumerate(windows):
        for j, (s2, f2) in enumerate(windows):
            if i < j and s1 < f2 and s2 < f1:
                overlapping += 1
    assert overlapping >= 5, f"expected substantial overlap, got {overlapping} overlapping pairs"

    assert result.max_observed_concurrency == 10
    assert result.max_observed_concurrency <= result.concurrency_cap
    assert result.spent_usd <= result.budget_cap_usd


@pytest.mark.asyncio
async def test_concurrency_cap_is_never_exceeded(monkeypatch):
    pool = _pool(monkeypatch, max_active_workers="3")
    tasks = [
        InferenceWorkerTask(system=_SYSMSG, user=f"n={i}", max_tokens=40, label=f"worker-{i}")
        for i in range(8)
    ]
    result = await pool.dispatch_batch(tasks)
    assert result.max_observed_concurrency <= 3
    assert result.dispatched == 8, result.results  # queued behind the semaphore, none silently dropped


@pytest.mark.asyncio
async def test_budget_cap_hard_refuses_without_spending(monkeypatch):
    pool = _pool(monkeypatch, max_usd="0.03")  # < one estimated call ($0.05)
    tasks = [
        InferenceWorkerTask(system=_SYSMSG, user=f"n={i}", max_tokens=20, label=f"worker-{i}")
        for i in range(3)
    ]
    result = await pool.dispatch_batch(tasks)
    assert result.dispatched == 0
    assert result.refused == 3
    assert result.spent_usd == 0.0
    for r in result.results:
        assert not r.ok
        assert "BUDGET_GUARD" in (r.error or "")
