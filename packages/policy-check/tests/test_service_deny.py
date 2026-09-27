"""Negative tests: this is a security control, so every deny path listed
in the M2 task must be exercised and confirmed to actually deny -- not
just "expected to" in a docstring somewhere.

Covers: off-range target, expired token, disallowed action type
(capability not granted), plus the other EXECUTION_POLICY.md §3.2 steps
(bad signature, world/range scope mismatch a.k.a. token spoofing, unknown
range, unreviewed ability, quota exceeded, human-approval-required) so the
whole authorize() surface has at least one real failing-closed test.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from ghostrange_contracts.enums import AbilityCategory, PolicyDenyReason
from ghostrange_contracts.policy import TargetRef

from ghostrange_policy_check import PolicyDenied

from conftest import make_request


def test_off_range_target_is_denied(
    service, world_id, provisioned_range, off_range_target, valid_token, actor, provenance
):
    """The primary T5/T10 backstop: a target that shares the range_id but
    was never actually provisioned into that range's registry entry must
    be denied, even though it passes the contract layer's own
    range-consistency check.
    """
    request = make_request(
        world_id=world_id, range_id=provisioned_range, target_refs=[off_range_target]
    )

    with pytest.raises(PolicyDenied) as excinfo:
        service.authorize(request, valid_token, actor=actor, provenance=provenance)

    assert excinfo.value.decision.allowed is False
    assert excinfo.value.decision.reason == PolicyDenyReason.TARGET_NOT_IN_RANGE
    assert service.audit_log.records[-1].decision == "DENY"
    assert service.audit_log.records[-1].reason == PolicyDenyReason.TARGET_NOT_IN_RANGE


def test_expired_token_is_denied(
    service, signer, world_id, provisioned_range, in_range_targets, actor, provenance
):
    """A token whose validity window has already elapsed (minted with both
    ``issued_at``/``expires_at`` in the past) must never be honored, even
    though its signature is otherwise perfectly valid.
    """
    import datetime as _dt

    long_ago = _dt.datetime.now(_dt.timezone.utc) - timedelta(hours=2)
    expired_token = signer.mint_token(
        world_id=world_id,
        range_id=provisioned_range,
        target_set=in_range_targets,
        capabilities=[AbilityCategory.RECON],
        ttl=timedelta(minutes=1),
        issued_at=long_ago,
    )
    request = make_request(
        world_id=world_id, range_id=provisioned_range, target_refs=[in_range_targets[0]]
    )

    with pytest.raises(PolicyDenied) as excinfo:
        service.authorize(request, expired_token, actor=actor, provenance=provenance)

    assert excinfo.value.decision.reason == PolicyDenyReason.TOKEN_EXPIRED


def test_disallowed_action_type_is_denied(
    service, world_id, provisioned_range, in_range_targets, valid_token, actor, provenance
):
    """``valid_token`` only grants RECON. A request for EXPLOIT (an action
    category the token was never issued for) must be denied even though
    the target itself is perfectly in-range.
    """
    request = make_request(
        world_id=world_id,
        range_id=provisioned_range,
        target_refs=[in_range_targets[0]],
        action_category=AbilityCategory.EXPLOIT,
    )

    with pytest.raises(PolicyDenied) as excinfo:
        service.authorize(request, valid_token, actor=actor, provenance=provenance)

    assert excinfo.value.decision.reason == PolicyDenyReason.CAPABILITY_NOT_GRANTED


def test_bad_token_signature_is_denied(
    service, world_id, provisioned_range, in_range_targets, valid_token, actor, provenance
):
    tampered_token = valid_token.model_copy(update={"issuer_signature": "0" * 64})
    request = make_request(
        world_id=world_id, range_id=provisioned_range, target_refs=[in_range_targets[0]]
    )

    with pytest.raises(PolicyDenied) as excinfo:
        service.authorize(request, tampered_token, actor=actor, provenance=provenance)

    assert excinfo.value.decision.reason == PolicyDenyReason.BAD_TOKEN_SIGNATURE


def test_token_world_spoofing_is_denied(
    service, signer, provisioned_range, in_range_targets, actor, provenance
):
    """A token minted for World A must not authorize a request claiming a
    different world_id (T16 -- token spoofing / cross-world reuse).
    """
    world_a = uuid.uuid4()
    world_b = uuid.uuid4()
    token_for_world_a = signer.mint_token(
        world_id=world_a,
        range_id=provisioned_range,
        target_set=in_range_targets,
        capabilities=[AbilityCategory.RECON],
        ttl=timedelta(minutes=10),
    )
    request_claiming_world_b = make_request(
        world_id=world_b, range_id=provisioned_range, target_refs=[in_range_targets[0]]
    )

    with pytest.raises(PolicyDenied) as excinfo:
        service.authorize(
            request_claiming_world_b, token_for_world_a, actor=actor, provenance=provenance
        )

    assert excinfo.value.decision.reason == PolicyDenyReason.TOKEN_SCOPE_MISMATCH


def test_unknown_range_is_denied(service, signer, world_id, in_range_targets, actor, provenance):
    """A range_id that was never registered (never provisioned, or already
    torn down) must fail closed -- never be treated as "no targets
    registered yet, permit anyway."
    """
    never_provisioned_range = uuid.uuid4()
    target_in_that_range = TargetRef(range_id=never_provisioned_range, host_or_ip="10.20.0.5")
    token = signer.mint_token(
        world_id=world_id,
        range_id=never_provisioned_range,
        target_set=[target_in_that_range],
        capabilities=[AbilityCategory.RECON],
        ttl=timedelta(minutes=10),
    )
    request = make_request(
        world_id=world_id, range_id=never_provisioned_range, target_refs=[target_in_that_range]
    )

    with pytest.raises(PolicyDenied) as excinfo:
        service.authorize(request, token, actor=actor, provenance=provenance)

    assert excinfo.value.decision.reason == PolicyDenyReason.UNKNOWN_RANGE


def test_unreviewed_ability_is_denied(
    service, world_id, provisioned_range, in_range_targets, valid_token, actor, provenance
):
    request = make_request(
        world_id=world_id,
        range_id=provisioned_range,
        target_refs=[in_range_targets[0]],
        ability_ref="attack.totally-unreviewed.custom-shell",
    )

    with pytest.raises(PolicyDenied) as excinfo:
        service.authorize(request, valid_token, actor=actor, provenance=provenance)

    assert excinfo.value.decision.reason == PolicyDenyReason.ABILITY_NOT_IN_CATALOG


def test_quota_exceeded_is_denied(
    service, registry, world_id, provisioned_range, in_range_targets, valid_token, actor,
    provenance,
):
    registry.set_quota(world_id, max_cost=10.0)
    request = make_request(
        world_id=world_id,
        range_id=provisioned_range,
        target_refs=[in_range_targets[0]],
        resource_cost=999.0,
    )

    with pytest.raises(PolicyDenied) as excinfo:
        service.authorize(request, valid_token, actor=actor, provenance=provenance)

    assert excinfo.value.decision.reason == PolicyDenyReason.QUOTA_EXCEEDED


def test_human_approval_required_and_missing_is_denied(
    service, registry, world_id, provisioned_range, in_range_targets, valid_token, actor,
    provenance,
):
    registry.human_approval_required_categories.add(AbilityCategory.RECON)
    request = make_request(
        world_id=world_id, range_id=provisioned_range, target_refs=[in_range_targets[0]]
    )

    with pytest.raises(PolicyDenied) as excinfo:
        service.authorize(request, valid_token, actor=actor, provenance=provenance)

    assert excinfo.value.decision.reason == PolicyDenyReason.HUMAN_APPROVAL_REQUIRED


def test_human_approval_required_and_present_is_allowed(
    service, registry, world_id, provisioned_range, in_range_targets, valid_token, actor,
    provenance,
):
    from ghostrange_policy_check import compute_request_hash

    registry.human_approval_required_categories.add(AbilityCategory.RECON)
    request = make_request(
        world_id=world_id, range_id=provisioned_range, target_refs=[in_range_targets[0]]
    )
    registry.record_approval(
        compute_request_hash(request), approver="human-1", ttl=timedelta(minutes=5)
    )

    decision = service.authorize(request, valid_token, actor=actor, provenance=provenance)
    assert decision.allowed is True


def test_a_denial_cannot_be_bypassed_by_renaming_the_task(
    service, world_id, provisioned_range, off_range_target, valid_token, actor, provenance
):
    """EXECUTION_POLICY.md §3.2: the check is per-request-hash, not
    per-task_id -- retrying the exact same denied request under a new
    task_id must still deny, because the request content (and therefore
    its hash) is unchanged.
    """
    first_request = make_request(
        world_id=world_id, range_id=provisioned_range, target_refs=[off_range_target]
    )
    with pytest.raises(PolicyDenied):
        service.authorize(first_request, valid_token, actor=actor, provenance=provenance)

    second_request = make_request(
        world_id=world_id, range_id=provisioned_range, target_refs=[off_range_target]
    )
    with pytest.raises(PolicyDenied) as excinfo:
        service.authorize(second_request, valid_token, actor=actor, provenance=provenance)
    assert excinfo.value.decision.reason == PolicyDenyReason.TARGET_NOT_IN_RANGE
    # two distinct task_ids, same denied content -- both attempts audited
    assert len(service.audit_log) == 2
    assert all(r.decision == "DENY" for r in service.audit_log.records)
