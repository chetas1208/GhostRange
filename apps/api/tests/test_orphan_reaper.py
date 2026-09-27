"""Unit tests for the general-purpose TTL orphan-reaper (orphan_reaper.py).

This is the safety net for exactly the incident class this feature exists
for: a GhostRange-owned Vultr Compute VM that outlives its ttl_seconds tag
regardless of which code path created (or failed to tear down) it. These
tests exercise the actual safety-relevant judgment calls:

- a worker within its TTL is left alone,
- a worker past its TTL is flagged and (when not a dry run) terminated,
- a worker with NO ttl_seconds tag at all is NEVER auto-reaped — this is a
  deliberate "no policy = leave alone" decision, not an oversight (see
  orphan_reaper.py's module docstring),
- one instance failing to terminate never stops the rest from being
  attempted, and is reported as a failure rather than swallowed,
- termination genuinely goes through ShieldedComputeProvider, so a handle
  that fails the ownership check is refused exactly as any other teardown
  path would refuse it -- reap_orphans cannot be used to bypass GhostShield.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from ghostrange_api.compute_provider import ComputeProvider, WorkerHandle
from ghostrange_api.config import Settings
from ghostrange_api.orphan_reaper import find_orphans, reap_orphans
from ghostrange_api.shielded_compute import ShieldedComputeProvider
from ghostrange_contracts.ghostshield_m17 import GhostShieldMode
from ghostrange_ghostshield import GatewayError, GhostExecutionGateway

NOW = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)


def _handle(
    compute_id: str,
    *,
    age_seconds: float,
    ttl_seconds: int | None,
) -> WorkerHandle:
    return WorkerHandle(
        provider="vultr",
        provider_compute_id=compute_id,
        world_ref="vpc-1",
        region="ewr",
        plan="vc2-1c-1gb",
        main_ip=None,
        created_at=NOW - timedelta(seconds=age_seconds),
        ttl_seconds=ttl_seconds,
    )


class FakeComputeProvider:
    """Minimal ComputeProvider double: a fixed set of handles, with
    optional per-id termination failures. Not wrapped in a shield -- used
    for the find_orphans/reap_orphans unit tests that are about the
    reaper's own age/ttl/error-handling logic, not GhostShield's policy."""

    def __init__(self, handles: list[WorkerHandle], *, fail_ids: set[str] | None = None) -> None:
        self._handles = {h.provider_compute_id: h for h in handles}
        self._fail_ids = fail_ids or set()
        self.terminate_calls: list[str] = []

    def list_all_ghostrange_workers(self) -> list[WorkerHandle]:
        return list(self._handles.values())

    def list_owned_workers(self, *, range_id: uuid.UUID | None = None) -> list[WorkerHandle]:
        return list(self._handles.values())

    def terminate_worker(self, handle: WorkerHandle) -> None:
        self.terminate_calls.append(handle.provider_compute_id)
        if handle.provider_compute_id in self._fail_ids:
            raise RuntimeError(f"simulated Vultr API failure destroying {handle.provider_compute_id}")
        del self._handles[handle.provider_compute_id]

    def create_worker(self, **kwargs):  # pragma: no cover - unused by these tests
        raise NotImplementedError

    def wait_ready(self, handle, *, timeout_s: float = 300.0):  # pragma: no cover
        raise NotImplementedError

    def run_benchmark(self, handle):  # pragma: no cover
        raise NotImplementedError

    def verify_api(self) -> None:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# find_orphans
# ---------------------------------------------------------------------------


def test_find_orphans_within_ttl_is_not_flagged():
    handle = _handle("i-fresh", age_seconds=60, ttl_seconds=3600)
    provider = FakeComputeProvider([handle])
    assert find_orphans(provider, now=NOW) == []


def test_find_orphans_past_ttl_is_flagged():
    handle = _handle("i-expired", age_seconds=7200, ttl_seconds=3600)
    provider = FakeComputeProvider([handle])
    orphans = find_orphans(provider, now=NOW)
    assert [h.provider_compute_id for h in orphans] == ["i-expired"]


def test_find_orphans_with_no_ttl_tag_is_never_flagged():
    """Explicit 'no policy = leave alone' case: even a VERY old handle with
    ttl_seconds=None must never be treated as an orphan -- an absent TTL
    tag is not evidence of abandonment, and auto-reaping it would risk
    destroying something a human deliberately created without an expiry."""
    ancient_no_ttl = _handle("i-no-ttl-ancient", age_seconds=10 * 365 * 24 * 3600, ttl_seconds=None)
    provider = FakeComputeProvider([ancient_no_ttl])
    assert find_orphans(provider, now=NOW) == []


def test_find_orphans_multiple_only_expired_returned():
    fresh = _handle("i-fresh", age_seconds=10, ttl_seconds=3600)
    expired_1 = _handle("i-expired-1", age_seconds=3601, ttl_seconds=3600)
    expired_2 = _handle("i-expired-2", age_seconds=99999, ttl_seconds=45 * 60)
    no_ttl = _handle("i-no-ttl", age_seconds=999999, ttl_seconds=None)
    provider = FakeComputeProvider([fresh, expired_1, expired_2, no_ttl])
    orphans = {h.provider_compute_id for h in find_orphans(provider, now=NOW)}
    assert orphans == {"i-expired-1", "i-expired-2"}


def test_find_orphans_exactly_at_ttl_boundary_not_flagged():
    """age == ttl is not yet "outlived" -- only strictly greater than."""
    handle = _handle("i-boundary", age_seconds=3600, ttl_seconds=3600)
    provider = FakeComputeProvider([handle])
    assert find_orphans(provider, now=NOW) == []


# ---------------------------------------------------------------------------
# reap_orphans (unit, no shield)
# ---------------------------------------------------------------------------


def test_reap_orphans_dry_run_finds_but_does_not_terminate():
    expired = _handle("i-expired", age_seconds=7200, ttl_seconds=3600)
    provider = FakeComputeProvider([expired])
    report = reap_orphans(provider, dry_run=True, now=NOW)
    assert report["dry_run"] is True
    assert [o["provider_compute_id"] for o in report["orphans_found"]] == ["i-expired"]
    assert report["would_terminate"] == ["i-expired"]
    assert report["terminated"] == []
    assert report["failed"] == []
    assert provider.terminate_calls == []  # never actually called


def test_reap_orphans_dry_run_false_terminates_each_exactly_once():
    expired_1 = _handle("i-expired-1", age_seconds=7200, ttl_seconds=3600)
    expired_2 = _handle("i-expired-2", age_seconds=9000, ttl_seconds=60)
    fresh = _handle("i-fresh", age_seconds=10, ttl_seconds=3600)
    provider = FakeComputeProvider([expired_1, expired_2, fresh])
    report = reap_orphans(provider, dry_run=False, now=NOW)
    assert report["dry_run"] is False
    assert sorted(report["terminated"]) == ["i-expired-1", "i-expired-2"]
    assert report["failed"] == []
    assert sorted(provider.terminate_calls) == ["i-expired-1", "i-expired-2"]
    # terminate_worker called exactly once per orphan, never for the fresh one
    assert provider.terminate_calls.count("i-expired-1") == 1
    assert provider.terminate_calls.count("i-expired-2") == 1
    assert "i-fresh" not in provider.terminate_calls
    # re-check confirms they are actually gone
    assert report["still_present_after_reap"] == []


def test_reap_orphans_one_failure_does_not_stop_the_others_and_is_reported():
    expired_1 = _handle("i-expired-1", age_seconds=7200, ttl_seconds=3600)
    expired_2 = _handle("i-expired-2", age_seconds=7200, ttl_seconds=3600)
    expired_3 = _handle("i-expired-3", age_seconds=7200, ttl_seconds=3600)
    provider = FakeComputeProvider(
        [expired_1, expired_2, expired_3], fail_ids={"i-expired-2"}
    )
    report = reap_orphans(provider, dry_run=False, now=NOW)
    # all three were attempted, regardless of the failure in the middle
    assert sorted(provider.terminate_calls) == ["i-expired-1", "i-expired-2", "i-expired-3"]
    assert sorted(report["terminated"]) == ["i-expired-1", "i-expired-3"]
    assert len(report["failed"]) == 1
    assert report["failed"][0]["provider_compute_id"] == "i-expired-2"
    assert "simulated Vultr API failure" in report["failed"][0]["error"]
    # never silently swallowed: it's neither in terminated nor just missing
    assert "i-expired-2" not in report["terminated"]


def test_reap_orphans_no_orphans_is_a_clean_noop():
    provider = FakeComputeProvider([_handle("i-fresh", age_seconds=10, ttl_seconds=3600)])
    report = reap_orphans(provider, dry_run=False, now=NOW)
    assert report["orphans_found"] == []
    assert report["terminated"] == []
    assert report["failed"] == []
    assert provider.terminate_calls == []


# ---------------------------------------------------------------------------
# reap_orphans genuinely goes through ShieldedComputeProvider's ownership
# check -- reusing the pattern from test_shielded_compute_ownership.py.
# ---------------------------------------------------------------------------


class FakeShieldInnerProvider:
    """Simulates a listing inconsistency: the discovery call the reaper
    uses (`list_all_ghostrange_workers`) surfaces a handle that the
    ownership check ShieldedComputeProvider.terminate_worker performs
    (`list_owned_workers(range_id=None)`) does NOT consider owned. This is
    exactly the scenario the ownership check exists to catch -- reap_orphans
    must not be able to terminate something on the strength of its own
    discovery call alone."""

    def __init__(self) -> None:
        self.terminate_calls: list[str] = []

    def list_all_ghostrange_workers(self) -> list[WorkerHandle]:
        return [_handle("foreign-instance-99", age_seconds=99999, ttl_seconds=60)]

    def list_owned_workers(self, *, range_id: uuid.UUID | None = None) -> list[WorkerHandle]:
        return []  # foreign-instance-99 is never in the owned set

    def terminate_worker(self, handle: WorkerHandle) -> None:
        # Must never run for the foreign id -- the ownership check has to
        # deny before the inner destroy effect is reached.
        self.terminate_calls.append(handle.provider_compute_id)

    def create_worker(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def wait_ready(self, handle, *, timeout_s: float = 300.0):  # pragma: no cover
        raise NotImplementedError

    def run_benchmark(self, handle):  # pragma: no cover
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _repo_root_env(monkeypatch):
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())


def test_reap_orphans_refuses_termination_for_unowned_handle_via_real_shield(monkeypatch):
    monkeypatch.setenv("GHOSTSHIELD_MODE", "ENFORCE")
    inner = FakeShieldInnerProvider()
    settings = Settings.from_env()
    gateway = GhostExecutionGateway(mode=GhostShieldMode.ENFORCE)
    shielded: ComputeProvider = ShieldedComputeProvider(inner, settings, gateway)

    report = reap_orphans(shielded, dry_run=False, now=NOW)

    # The reaper's own discovery call did find it (it looked TTL-expired)...
    assert [o["provider_compute_id"] for o in report["orphans_found"]] == ["foreign-instance-99"]
    # ...but the shield's ownership check (P1_UNOWNED_RESOURCE) refused the
    # actual termination, and reap_orphans reported that as a failure
    # rather than crashing or silently pretending it succeeded.
    assert report["terminated"] == []
    assert len(report["failed"]) == 1
    assert report["failed"][0]["provider_compute_id"] == "foreign-instance-99"
    assert "P1_UNOWNED_RESOURCE" in report["failed"][0]["error"]
    # The inner provider's actual destroy effect never ran.
    assert inner.terminate_calls == []
