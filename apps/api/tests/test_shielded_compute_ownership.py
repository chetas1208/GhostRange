"""Proves the ownership gap found during M20 live-deployment closure is
fixed end-to-end: ShieldedComputeProvider.terminate_worker() must refuse
(via GhostShield's P1_UNOWNED_RESOURCE policy) any instance id that is not
in the *properly filtered* owned set — i.e. an inner ComputeProvider whose
`list_owned_workers(range_id=None)` correctly excludes foreign/untagged
instances (as RealVultrProvider.list_computes / MockVultrProvider.list_computes
now do) must cause the gateway to deny termination of an id outside that set,
and the inner provider's actual destroy effect must never run.

This uses a small hand-rolled ComputeProvider double rather than
RealVultrProvider/MockVultrProvider directly so the test is not coupled to
*how* those providers filter — only to the ShieldedComputeProvider contract:
"resource_owned is computed from list_owned_workers(range_id=None), and an
id absent from that list is denied."
"""

from __future__ import annotations

import os
import uuid

import pytest

from ghostrange_api.compute_provider import WorkerHandle
from ghostrange_api.config import Settings
from ghostrange_api.shielded_compute import ShieldedComputeProvider
from ghostrange_contracts.ghostshield_m17 import GhostShieldMode
from ghostrange_ghostshield import GatewayError, GhostExecutionGateway


class FakeMixedOwnershipProvider:
    """Stands in for a real Vultr account containing both GhostRange-owned
    (tagged) instances and foreign/untagged ones. `list_owned_workers`
    mimics the *fixed* filtering behavior: only owned ids are ever
    returned, regardless of `range_id`.
    """

    def __init__(self, *, owned_ids: set[str], foreign_ids: set[str]) -> None:
        self._owned_ids = set(owned_ids)
        self._foreign_ids = set(foreign_ids)
        self.terminate_calls: list[str] = []

    def _handle(self, compute_id: str) -> WorkerHandle:
        return WorkerHandle(
            provider="vultr",
            provider_compute_id=compute_id,
            world_ref="vpc-owned",
            region="ewr",
            plan="vc2-1c-1gb",
            main_ip=None,
        )

    def list_owned_workers(self, *, range_id: uuid.UUID | None = None) -> list[WorkerHandle]:
        # Correctly-filtered behavior: foreign/untagged ids never appear,
        # whether range_id is None (teardown-time "list everything we own")
        # or a specific range.
        return [self._handle(cid) for cid in self._owned_ids]

    def list_all_ghostrange_workers(self) -> list[WorkerHandle]:
        return self.list_owned_workers(range_id=None)

    def terminate_worker(self, handle: WorkerHandle) -> None:
        # If this ever runs for a foreign id, the ownership check failed
        # to do its job — the gateway must deny before reaching here.
        self.terminate_calls.append(handle.provider_compute_id)
        self._owned_ids.discard(handle.provider_compute_id)
        self._foreign_ids.discard(handle.provider_compute_id)

    # Unused by this test but required to satisfy the ComputeProvider
    # Protocol's shape if anything introspects it.
    def create_worker(self, **kwargs):  # noqa: D401
        raise NotImplementedError

    def wait_ready(self, handle, *, timeout_s: float = 300.0):
        raise NotImplementedError

    def run_benchmark(self, handle):
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _repo_root_env(monkeypatch):
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())


def _shielded(inner: FakeMixedOwnershipProvider) -> ShieldedComputeProvider:
    monkeypatch_settings = Settings.from_env()
    gw = GhostExecutionGateway(mode=GhostShieldMode.ENFORCE)
    return ShieldedComputeProvider(inner, monkeypatch_settings, gw)


def test_terminate_worker_denies_foreign_instance_not_in_owned_set(monkeypatch):
    monkeypatch.setenv("GHOSTSHIELD_MODE", "ENFORCE")
    inner = FakeMixedOwnershipProvider(owned_ids={"owned-instance-1"}, foreign_ids={"foreign-instance-99"})
    shield = _shielded(inner)

    foreign_handle = WorkerHandle(
        provider="vultr",
        provider_compute_id="foreign-instance-99",
        world_ref="",
        region="ewr",
        plan="vc2-1c-1gb",
        main_ip=None,
    )

    with pytest.raises(GatewayError, match="P1_UNOWNED_RESOURCE"):
        shield.terminate_worker(foreign_handle)

    # The inner provider's actual destroy effect must never have run.
    assert inner.terminate_calls == []
    assert "foreign-instance-99" in inner._foreign_ids


def test_terminate_worker_allows_owned_instance(monkeypatch):
    monkeypatch.setenv("GHOSTSHIELD_MODE", "ENFORCE")
    inner = FakeMixedOwnershipProvider(owned_ids={"owned-instance-1"}, foreign_ids={"foreign-instance-99"})
    shield = _shielded(inner)

    owned_handle = WorkerHandle(
        provider="vultr",
        provider_compute_id="owned-instance-1",
        world_ref="",
        region="ewr",
        plan="vc2-1c-1gb",
        main_ip=None,
    )

    # Sanity: control case — a genuinely owned id is allowed through and
    # the inner destroy effect runs exactly once.
    shield.terminate_worker(owned_handle)
    assert inner.terminate_calls == ["owned-instance-1"]


class FakeSingleCapProvider(FakeMixedOwnershipProvider):
    """Same as above, plus a real create_worker so create_worker's own cap
    check (via _auth_ctx) can be exercised, not just terminate_worker's."""

    def create_worker(self, **kwargs):
        new_id = f"new-instance-{len(self._owned_ids)}"
        self._owned_ids.add(new_id)
        return self._handle(new_id)


def test_create_worker_cap_is_global_not_scoped_to_the_calling_range_id(monkeypatch):
    """Real incident, 2026-09-27: campaign_routes.py mints a FRESH range_id
    on every call to POST /v1/campaigns/golden. _auth_ctx() used to count
    list_owned_workers(range_id=<that fresh id>), which is always 0 for a
    brand-new range regardless of how many real VMs already exist
    account-wide - so MAX_ACTIVE_COMPUTE_WORKERS never actually gated this
    call path, and 4 real orphaned Vultr VMs got created before anyone
    noticed. This proves the fix: the cap must be checked against ALL
    globally-owned workers, not the specific range_id of the current call.
    """
    monkeypatch.setenv("GHOSTSHIELD_MODE", "ENFORCE")
    monkeypatch.setenv("MAX_ACTIVE_COMPUTE_WORKERS", "1")
    # One worker already exists, owned by a DIFFERENT, already-finished range.
    inner = FakeSingleCapProvider(owned_ids={"already-running-instance"}, foreign_ids=set())
    shield = _shielded(inner)

    # A brand-new range_id, exactly like campaign_routes.py's uuid.uuid4() per call.
    fresh_range_id = uuid.uuid4()

    with pytest.raises(GatewayError, match="P2_MAX_ACTIVE_WORKERS|MAX_ACTIVE"):
        shield.create_worker(range_id=fresh_range_id, experiment_id=None)

    # No second VM was created - the cap held even though this range_id had
    # never itself created anything before.
    assert len(inner._owned_ids) == 1
