from __future__ import annotations

from ghostrange_policy_check import redact_secrets
from ghostrange_policy_check.secrets import REDACTED


def test_redacts_known_secret_shaped_fields():
    data = {
        "vultr_api_key": "AAAABBBBCCCC",
        "caldera_admin_api_key": "supersecret",
        "db_password": "hunter2",
        "task_id": "not-a-secret",
    }
    out = redact_secrets(data)
    assert out["vultr_api_key"] == REDACTED
    assert out["caldera_admin_api_key"] == REDACTED
    assert out["db_password"] == REDACTED
    assert out["task_id"] == "not-a-secret"


def test_does_not_over_redact_token_id_or_ticket_id():
    """token_id/ticket_id/request_hash are useful, non-secret bookkeeping
    fields -- a bare "token" denylist entry would wrongly redact these.
    """
    data = {"token_id": "abc-123", "ticket_id": "def-456", "request_hash": "deadbeef"}
    out = redact_secrets(data)
    assert out == data


def test_redacts_nested_dicts_and_lists():
    data = {
        "outer": {"api_key": "AAAA", "safe": "ok"},
        "items": [{"password": "x"}, {"safe": "y"}],
    }
    out = redact_secrets(data)
    assert out["outer"]["api_key"] == REDACTED
    assert out["outer"]["safe"] == "ok"
    assert out["items"][0]["password"] == REDACTED
    assert out["items"][1]["safe"] == "y"
