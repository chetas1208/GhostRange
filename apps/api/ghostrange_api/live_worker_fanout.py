"""Real parallel-worker fan-out for the live M20 golden campaign path.

Extracted from campaign_routes.py so it's directly unit-testable without a
running Postgres/Redis stack (the route itself only exercises this branch
when app.state.worker_orchestrator is wired, which requires a real DB pool -
that meant this logic previously had zero coverage in the default test
suite, an unacceptable gap given the 2026-09-27 uncapped-worker-creation
incident this whole enforcement path exists to prevent).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol


class FanOutComputeProvider(Protocol):
    def list_all_ghostrange_workers(self) -> list[Any]: ...


@dataclass
class FanOutResult:
    requested: int
    successes: list[Any] = field(default_factory=list)
    failures: list[BaseException] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return len(self.successes)

    @property
    def failed(self) -> int:
        return len(self.failures)

    def to_summary(self) -> dict[str, int]:
        return {"requested": self.requested, "succeeded": self.succeeded, "failed": self.failed}


def compute_fan_out_count(*, cap: int, currently_owned: int, planned: int) -> int:
    """How many real workers to attempt launching right now.

    Reserves capacity against the cap BEFORE any creation is attempted, using
    the caller-supplied `currently_owned` count taken synchronously (no
    `await` between that read and this computation - asyncio has no
    preemption between await points on one event loop, so this can't race
    with another concurrent request handled by the same process). The real
    enforcement inside each create_worker() call (ShieldedComputeProvider ->
    GhostExecutionGateway) is still the authoritative backstop; this is
    defense-in-depth against ever attempting more launches than the cap
    could admit, not a replacement for that check.

    `planned` is the scheduler's own sizing (golden_path.py's
    worker_slots_planned, already bounded by the same cap and by how much of
    the task graph is genuinely parallelizable) - this function additionally
    bounds it against whatever headroom is ACTUALLY left right now, which
    can be less than the full cap if other workers are already running.

    Always returns at least 1: a live campaign that decides to run a worker
    at all must attempt at least one, even if the plan/cap math rounds to
    zero (e.g. a scenario with only one task) - available==0 is the one case
    that legitimately returns 0, since the cap is genuinely exhausted.
    """
    available = max(0, cap - currently_owned)
    if available == 0:
        return 0
    return max(1, min(max(1, planned), available))


async def run_worker_fan_out(
    *,
    worker_fn: Callable[[], Awaitable[Any]],
    count: int,
) -> FanOutResult:
    """Launch `count` real worker lifecycles concurrently, isolating failures.

    One worker's exception (e.g. a failed teardown) never prevents the
    others from completing or being reported - every outcome, success or
    failure, is captured. This is the fix for the exact failure mode behind
    today's incident: a swallowed exception on one worker must never hide
    what happened to it.
    """
    if count <= 0:
        return FanOutResult(requested=0)
    outcomes = await asyncio.gather(*[worker_fn() for _ in range(count)], return_exceptions=True)
    result = FanOutResult(requested=count)
    for outcome in outcomes:
        if isinstance(outcome, BaseException):
            result.failures.append(outcome)
        else:
            result.successes.append(outcome)
    return result
