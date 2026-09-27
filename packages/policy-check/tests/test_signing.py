from __future__ import annotations

from datetime import timedelta

import pytest
from ghostrange_contracts.enums import AbilityCategory


def test_signer_refuses_short_key():
    from ghostrange_policy_check import TokenSigner

    with pytest.raises(ValueError):
        TokenSigner(key=b"short")


def test_signer_refuses_missing_key_and_env_var(monkeypatch):
    from ghostrange_policy_check import TokenSigner

    monkeypatch.delenv(TokenSigner.ENV_VAR, raising=False)
    with pytest.raises(RuntimeError):
        TokenSigner()


def test_verify_token_rejects_any_field_tamper(signer, world_id, range_id, in_range_targets):
    token = signer.mint_token(
        world_id=world_id,
        range_id=range_id,
        target_set=in_range_targets,
        capabilities=[AbilityCategory.RECON],
        ttl=timedelta(minutes=5),
    )
    assert signer.verify_token(token) is True

    tampered = token.model_copy(update={"capabilities": [AbilityCategory.EXPLOIT]})
    assert signer.verify_token(tampered) is False


def test_verify_ticket_rejects_wrong_hash_and_expired(signer):
    ticket = signer.issue_ticket("abc123", ttl=timedelta(seconds=30))
    assert signer.verify_ticket(ticket, expected_request_hash="abc123") is True
    assert signer.verify_ticket(ticket, expected_request_hash="wrong-hash") is False

    import datetime as _dt

    long_ago = _dt.datetime.now(_dt.timezone.utc) - timedelta(hours=1)
    expired_ticket = signer.issue_ticket(
        "abc123", ttl=timedelta(seconds=30), issued_at=long_ago
    )
    assert signer.verify_ticket(expired_ticket, expected_request_hash="abc123") is False
