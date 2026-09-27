"""M17 bypass close: orchestrator.py's VultrAdaptedComputeProvider path.

Before this fix, ``M2OneWorldOrchestrator._build_provider`` returned a raw
``VultrAdaptedComputeProvider`` (wrapping ``RealVultrProvider`` when
``GHOSTRANGE_LIVE_PROVIDER=vultr``) with no GhostShield mediation at all —
``start_provisioning``/``start_destroy`` drove real Vultr create_world/
create_compute/destroy_compute/destroy_world calls regardless of
GHOSTSHIELD_MODE. These tests prove the real Vultr-effect calls never fire
unless GhostExecutionGateway issues ALLOW, and that ENFORCE/LOCKDOWN fail
closed (no fallback to the unmediated inner adapter).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field

import pytest

from ghostrange_api.compute_provider import MockComputeProvider
from ghostrange_api.config import Settings
from ghostrange_api.orchestrator import ActiveRun, M2OneWorldOrchestrator
from ghostrange_api.shielded_vultr_adapter import ShieldedVultrAdapter
from ghostrange_contracts.ghostshield_m17 import GhostShieldMode
from ghostrange_ghostshield import GatewayError, GhostExecutionGateway


@dataclass
class _FakeSpec:
    assets: list = field(default_factory=lambda: [object(), object()])


class _RecordingInner:
    """Structurally satisfies RangeWorldProvider; records real-effect calls."""

    def __init__(self) -> None:
        self.provisioning_calls: list[tuple] = []
        self.destroy_calls: list[tuple] = []

    def start_provisioning(self, *, range_id, world_id, spec, correlation_id) -> None:
        self.provisioning_calls.append((range_id, world_id, correlation_id))

    def get_state(self, *, range_id, world_id):
        return "unused-in-these-tests"

    def start_destroy(self, *, range_id, world_id, correlation_id) -> None:
        self.destroy_calls.append((range_id, world_id, correlation_id))


def _settings(monkeypatch, mode: str) -> Settings:
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.setenv("GHOSTSHIELD_MODE", mode)
    return Settings.from_env()


def test_lockdown_blocks_real_provisioning_and_never_calls_inner(monkeypatch):
    settings = _settings(monkeypatch, "LOCKDOWN")
    inner = _RecordingInner()
    gw = GhostExecutionGateway(mode=GhostShieldMode.LOCKDOWN)
    shield = ShieldedVultrAdapter(inner, settings, gw)
    with pytest.raises(GatewayError, match="LOCKDOWN"):
        shield.start_provisioning(
            range_id=uuid.uuid4(), world_id=uuid.uuid4(), spec=_FakeSpec(), correlation_id="c1"
        )
    assert inner.provisioning_calls == [], "real create_world/create_compute must never fire under LOCKDOWN"


def test_enforce_allow_reaches_inner_and_tracks_ownership_for_destroy(monkeypatch):
    settings = _settings(monkeypatch, "ENFORCE")
    inner = _RecordingInner()
    gw = GhostExecutionGateway(mode=GhostShieldMode.ENFORCE)
    shield = ShieldedVultrAdapter(inner, settings, gw)
    rid, wid = uuid.uuid4(), uuid.uuid4()

    shield.start_provisioning(range_id=rid, world_id=wid, spec=_FakeSpec(), correlation_id="c2")
    assert len(inner.provisioning_calls) == 1

    shield.start_destroy(range_id=rid, world_id=wid, correlation_id="c2")
    assert len(inner.destroy_calls) == 1


def test_enforce_denies_destroy_of_unowned_world(monkeypatch):
    """P1 (never terminate an unowned resource) now also covers DESTROY_WORLD."""
    settings = _settings(monkeypatch, "ENFORCE")
    inner = _RecordingInner()
    gw = GhostExecutionGateway(mode=GhostShieldMode.ENFORCE)
    shield = ShieldedVultrAdapter(inner, settings, gw)
    rid, wid = uuid.uuid4(), uuid.uuid4()

    # start_destroy called for a (range_id, world_id) this adapter never
    # provisioned itself -> resource_owned=False -> P1 DENY, inner never called.
    with pytest.raises(GatewayError, match="DENY"):
        shield.start_destroy(range_id=rid, world_id=wid, correlation_id="c3")
    assert inner.destroy_calls == [], "real destroy_compute/destroy_world must never fire for an unowned world"


def test_orchestrator_build_provider_wraps_live_and_mock_when_enforce(monkeypatch):
    settings = _settings(monkeypatch, "ENFORCE")
    orch = M2OneWorldOrchestrator(
        gateway=None,  # not used by _build_provider
        range_dir=settings.range_dir,
        settings=settings,
        live_provider="mock",
    )
    run = ActiveRun(range_id=uuid.uuid4(), world_id=uuid.uuid4())
    provider = orch._build_provider(run)
    assert isinstance(provider, ShieldedVultrAdapter), (
        "orchestrator must not hand back an unshielded VultrAdaptedComputeProvider under ENFORCE"
    )


def test_orchestrator_build_provider_unshielded_only_on_explicit_disabled(monkeypatch):
    settings = _settings(monkeypatch, "DISABLED")
    orch = M2OneWorldOrchestrator(
        gateway=None,
        range_dir=settings.range_dir,
        settings=settings,
        live_provider="mock",
    )
    run = ActiveRun(range_id=uuid.uuid4(), world_id=uuid.uuid4())
    provider = orch._build_provider(run)
    assert not isinstance(provider, ShieldedVultrAdapter)
