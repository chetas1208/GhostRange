"""Compute VM concurrency and inference-pool concurrency are separate knobs.

Real Vultr Compute VMs are billable infrastructure and must stay capped low by
default; Serverless Inference calls have no VM lifecycle and may run at a much
higher concurrency. A single shared env var must never let one accidentally
raise the other.
"""
from ghostrange_api.config import Settings

_RELEVANT_KEYS = (
    "MAX_ACTIVE_WORKERS",
    "MAX_ACTIVE_COMPUTE_WORKERS",
    "MAX_ACTIVE_INFERENCE_WORKERS",
)


def _settings(monkeypatch, **env_overrides) -> Settings:
    for key in _RELEVANT_KEYS:
        monkeypatch.delenv(key, raising=False)
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, str(value))
    return Settings.from_env()


def test_default_compute_cap_is_one(monkeypatch):
    s = _settings(monkeypatch)
    assert s.compute_worker_concurrency_cap == 1


def test_inference_cap_can_be_ten_independent_of_compute_cap(monkeypatch):
    s = _settings(monkeypatch, MAX_ACTIVE_COMPUTE_WORKERS=1, MAX_ACTIVE_INFERENCE_WORKERS=10)
    assert s.compute_worker_concurrency_cap == 1
    assert s.inference_worker_concurrency_cap == 10


def test_raising_inference_cap_never_raises_compute_cap(monkeypatch):
    s = _settings(monkeypatch, MAX_ACTIVE_COMPUTE_WORKERS=1, MAX_ACTIVE_INFERENCE_WORKERS=999)
    assert s.compute_worker_concurrency_cap == 1
    assert s.inference_worker_concurrency_cap == 10  # still hard-clamped


def test_inference_hard_ceiling_cannot_be_exceeded(monkeypatch):
    s = _settings(monkeypatch, MAX_ACTIVE_INFERENCE_WORKERS=500)
    assert s.inference_worker_concurrency_cap == 10 == s.INFERENCE_WORKER_HARD_CEILING


def test_compute_cap_has_no_permissive_hard_ceiling_raise(monkeypatch):
    s = _settings(monkeypatch, MAX_ACTIVE_COMPUTE_WORKERS=1)
    assert s.compute_worker_concurrency_cap == 1


def test_legacy_max_active_workers_still_used_as_fallback_when_new_vars_unset(monkeypatch):
    # Backward compatibility: an old .env with only MAX_ACTIVE_WORKERS=10 set (no split
    # vars) must not silently grant 10 concurrent real Vultr Compute VMs.
    s = _settings(monkeypatch, MAX_ACTIVE_WORKERS=10)
    assert s.compute_worker_concurrency_cap == 1, (
        "legacy MAX_ACTIVE_WORKERS must not raise the compute cap above the safe default"
    )
    assert s.inference_worker_concurrency_cap == 10
