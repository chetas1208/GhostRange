"""NETBIRD_ENABLED must be a real feature flag: false (the current,
committed default) means the NetBird integration is entirely inert, with
no env var able to accidentally half-enable it.
"""

from __future__ import annotations

from ghostrange_api.config import Settings

_KEYS = (
    "NETBIRD_ENABLED",
    "NETBIRD_API_TOKEN",
    "NETBIRD_WORKER_SETUP_KEY",
    "NETBIRD_WORKER_GROUP",
    "NETBIRD_API_BASE_URL",
    "NETBIRD_ENROLL_TIMEOUT_S",
)


def _settings(monkeypatch, **overrides) -> Settings:
    for key in _KEYS:
        monkeypatch.delenv(key, raising=False)
    for key, value in overrides.items():
        monkeypatch.setenv(key, str(value))
    return Settings.from_env()


def test_default_is_disabled(monkeypatch):
    s = _settings(monkeypatch)
    assert s.netbird_enabled is False
    assert s.netbird_configured is False


def test_default_group_and_base_url(monkeypatch):
    s = _settings(monkeypatch)
    assert s.netbird_worker_group == "ghostrange-workers"
    assert s.netbird_api_base_url == "https://api.netbird.io"


def test_enabled_true_variants(monkeypatch):
    for truthy in ("1", "true", "True", "yes", "YES"):
        s = _settings(monkeypatch, NETBIRD_ENABLED=truthy)
        assert s.netbird_enabled is True, f"{truthy!r} should enable the flag"


def test_disabled_variants_and_unset(monkeypatch):
    for falsy in ("0", "false", "no", ""):
        s = _settings(monkeypatch, NETBIRD_ENABLED=falsy)
        assert s.netbird_enabled is False, f"{falsy!r} should not enable the flag"


def test_netbird_configured_requires_enabled_and_both_credentials(monkeypatch):
    s = _settings(monkeypatch, NETBIRD_ENABLED="true", NETBIRD_API_TOKEN="tok")
    assert s.netbird_configured is False  # missing setup key

    s = _settings(monkeypatch, NETBIRD_ENABLED="true", NETBIRD_WORKER_SETUP_KEY="key")
    assert s.netbird_configured is False  # missing token

    s = _settings(monkeypatch, NETBIRD_ENABLED="true", NETBIRD_API_TOKEN="tok", NETBIRD_WORKER_SETUP_KEY="key")
    assert s.netbird_configured is True


def test_credentials_present_but_disabled_is_still_not_configured(monkeypatch):
    """A stray token/setup key in the environment must never activate the
    feature on its own — only NETBIRD_ENABLED=true does that."""
    s = _settings(monkeypatch, NETBIRD_ENABLED="false", NETBIRD_API_TOKEN="tok", NETBIRD_WORKER_SETUP_KEY="key")
    assert s.netbird_enabled is False
    assert s.netbird_configured is False
