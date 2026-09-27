"""M17: ENFORCE mode blocks over-limit worker create (mock provider)."""

from __future__ import annotations

import os
import uuid

import pytest

from ghostrange_api.compute_provider import MockComputeProvider, build_compute_provider
from ghostrange_api.config import Settings
from ghostrange_api.shielded_compute import ShieldedComputeProvider
from ghostrange_contracts.ghostshield_m17 import GhostShieldMode
from ghostrange_ghostshield import GhostExecutionGateway, GatewayError


def test_enforce_denies_second_worker_create(monkeypatch):
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.setenv("MAX_ACTIVE_WORKERS", "1")
    monkeypatch.setenv("GHOSTSHIELD_MODE", "ENFORCE")
    settings = Settings.from_env()
    inner = MockComputeProvider()
    gw = GhostExecutionGateway(mode=GhostShieldMode.ENFORCE)
    shield = ShieldedComputeProvider(inner, settings, gw)
    rid = uuid.uuid4()
    shield.create_worker(range_id=rid, experiment_id=None, worker_id=uuid.uuid4())
    with pytest.raises(GatewayError, match="DENY"):
        shield.create_worker(range_id=rid, experiment_id=None, worker_id=uuid.uuid4())


def test_build_compute_provider_wraps_when_not_disabled(monkeypatch):
    monkeypatch.setenv("GHOSTSHIELD_MODE", "ENFORCE")
    monkeypatch.setenv("GHOSTRANGE_REPO_ROOT", os.getcwd())
    monkeypatch.delenv("GHOSTSCHEDULER_LIVE", raising=False)
    settings = Settings.from_env()
    provider = build_compute_provider(settings)
    assert isinstance(provider, ShieldedComputeProvider)
