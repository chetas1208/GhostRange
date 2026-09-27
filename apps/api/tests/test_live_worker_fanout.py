"""Real, DB-free unit tests for the live campaign's parallel-worker fan-out.

campaign_routes.py's live-worker branch only executes when a real Postgres
pool is wired (app.state.worker_orchestrator), so the default fast test
suite never exercised this logic before it was extracted into
live_worker_fanout.py. These tests close that gap directly.
"""
from __future__ import annotations

import asyncio

import pytest

from ghostrange_api.live_worker_fanout import compute_fan_out_count, run_worker_fan_out


class TestComputeFanOutCount:
    def test_bounded_by_cap_not_just_plan(self):
        # Real incident 2026-09-27: the plan alone must never be trusted -
        # the cap is authoritative headroom.
        assert compute_fan_out_count(cap=10, currently_owned=0, planned=10) == 10
        assert compute_fan_out_count(cap=3, currently_owned=0, planned=10) == 3

    def test_bounded_by_already_owned_workers(self):
        # 10-cap, 7 already running -> only 3 more slots available, even if
        # the plan asked for 10.
        assert compute_fan_out_count(cap=10, currently_owned=7, planned=10) == 3

    def test_zero_when_cap_exhausted(self):
        assert compute_fan_out_count(cap=1, currently_owned=1, planned=5) == 0
        assert compute_fan_out_count(cap=5, currently_owned=5, planned=1) == 0

    def test_never_exceeds_cap_even_with_huge_plan(self):
        assert compute_fan_out_count(cap=10, currently_owned=0, planned=9999) == 10

    def test_at_least_one_when_plan_is_zero_but_capacity_exists(self):
        # A degenerate plan (0 planned) still attempts one worker if the
        # cap allows it - matches "always attempt at least one" contract.
        assert compute_fan_out_count(cap=10, currently_owned=0, planned=0) == 1

    def test_single_worker_default(self):
        assert compute_fan_out_count(cap=1, currently_owned=0, planned=1) == 1


class TestRunWorkerFanOut:
    @pytest.mark.asyncio
    async def test_zero_count_returns_empty_result_no_calls(self):
        calls = []

        async def worker():
            calls.append(1)
            return "ok"

        result = await run_worker_fan_out(worker_fn=worker, count=0)
        assert result.requested == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert calls == []

    @pytest.mark.asyncio
    async def test_all_succeed(self):
        async def worker():
            await asyncio.sleep(0)
            return {"ok": True}

        result = await run_worker_fan_out(worker_fn=worker, count=5)
        assert result.requested == 5
        assert result.succeeded == 5
        assert result.failed == 0
        assert len(result.successes) == 5

    @pytest.mark.asyncio
    async def test_one_failure_does_not_stop_or_hide_the_others(self):
        # This is the exact failure mode behind the 2026-09-27 incident:
        # one worker's exception must never swallow or block the rest.
        call_count = {"n": 0}

        async def worker():
            call_count["n"] += 1
            my_index = call_count["n"]
            if my_index == 3:
                raise RuntimeError("simulated teardown failure on worker 3")
            return f"worker-{my_index}-ok"

        result = await run_worker_fan_out(worker_fn=worker, count=5)
        assert result.requested == 5
        assert call_count["n"] == 5  # all 5 were actually attempted
        assert result.succeeded == 4
        assert result.failed == 1
        assert isinstance(result.failures[0], RuntimeError)
        assert "worker 3" in str(result.failures[0])

    @pytest.mark.asyncio
    async def test_all_fail_reports_every_failure(self):
        async def worker():
            raise ValueError("boom")

        result = await run_worker_fan_out(worker_fn=worker, count=3)
        assert result.requested == 3
        assert result.succeeded == 0
        assert result.failed == 3
        assert all(isinstance(f, ValueError) for f in result.failures)

    @pytest.mark.asyncio
    async def test_workers_actually_run_concurrently_not_sequentially(self):
        # Prove this is real concurrent fan-out, not a disguised loop: 5
        # workers that each sleep 0.05s should complete in ~0.05s total,
        # not ~0.25s, if genuinely concurrent.
        import time

        async def worker():
            await asyncio.sleep(0.05)
            return "done"

        start = time.monotonic()
        result = await run_worker_fan_out(worker_fn=worker, count=5)
        elapsed = time.monotonic() - start
        assert result.succeeded == 5
        assert elapsed < 0.2  # generous margin, but rules out 0.25s+ sequential

    def test_to_summary_shape(self):
        from ghostrange_api.live_worker_fanout import FanOutResult

        r = FanOutResult(requested=3, successes=["a", "b"], failures=[RuntimeError("x")])
        assert r.to_summary() == {"requested": 3, "succeeded": 2, "failed": 1}
