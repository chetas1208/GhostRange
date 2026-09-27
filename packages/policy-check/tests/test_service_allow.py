"""Positive-path tests: a well-formed, in-scope request against a valid
token is allowed, produces a verifiable ticket, and is audited.
"""

from __future__ import annotations

from ghostrange_policy_check import compute_request_hash

from conftest import make_request


def test_authorize_allows_in_scope_request(
    service, world_id, provisioned_range, in_range_targets, valid_token, actor, provenance
):
    request = make_request(
        world_id=world_id, range_id=provisioned_range, target_refs=[in_range_targets[0]]
    )

    decision = service.authorize(request, valid_token, actor=actor, provenance=provenance)

    assert decision.allowed is True
    assert decision.reason is None
    assert decision.ticket is not None
    assert decision.request_hash == compute_request_hash(request)


def test_allowed_ticket_verifies_for_the_executor(
    service, signer, world_id, provisioned_range, in_range_targets, valid_token, actor, provenance
):
    request = make_request(
        world_id=world_id, range_id=provisioned_range, target_refs=[in_range_targets[0]]
    )
    decision = service.authorize(request, valid_token, actor=actor, provenance=provenance)

    # Defense-in-depth: the executor (adversary-adapter/range-runtime/
    # vultr-control) independently re-verifies the ticket before acting.
    assert signer.verify_ticket(decision.ticket, expected_request_hash=decision.request_hash)

    # A ticket bound to a DIFFERENT request hash must not verify.
    assert not signer.verify_ticket(decision.ticket, expected_request_hash="not-the-real-hash")


def test_allow_is_recorded_in_the_audit_log(
    service, world_id, provisioned_range, in_range_targets, valid_token, actor, provenance
):
    request = make_request(
        world_id=world_id, range_id=provisioned_range, target_refs=[in_range_targets[0]]
    )
    service.authorize(request, valid_token, actor=actor, provenance=provenance)

    assert len(service.audit_log) == 1
    record = service.audit_log.records[0]
    assert record.decision == "ALLOW"
    assert record.reason is None
    assert service.audit_log.verify_chain()
