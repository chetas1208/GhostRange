import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from ghostrange_contracts.enums import AbilityCategory, PolicyActorKind, PolicyDenyReason
from ghostrange_contracts.policy import (
    ActorRef,
    AuditRecordV1,
    BudgetV1,
    ExecutionRequestV1,
    ExecutionTicketV1,
    PolicyDecisionV1,
    PolicyV1,
    ProvenanceRef,
    RangeOwnershipTokenV1,
    TargetRef,
)


def _now():
    return datetime.now(timezone.utc)


def test_policy_deny_overrides_allow():
    policy = PolicyV1(
        name="default-safety-boundary",
        allowed_actions=["scan.port", "exec.shell"],
        denied_actions=["exec.shell"],
    )
    assert policy.permits("scan.port") is True
    assert policy.permits("exec.shell") is False


def test_policy_deny_by_default():
    policy = PolicyV1(name="empty-allowlist")
    assert policy.permits("anything") is False


def test_budget_is_exhausted_and_remaining():
    budget = BudgetV1(
        range_id=uuid.uuid4(),
        max_total_cost_usd=100.0,
        spent_cost_usd=40.0,
        max_duration_seconds=3600,
    )
    assert budget.is_exhausted is False
    assert budget.remaining_usd == 60.0

    budget.spent_cost_usd = 150.0
    assert budget.is_exhausted is True
    assert budget.remaining_usd == 0.0


def test_budget_rejects_non_positive_max_cost():
    with pytest.raises(ValidationError):
        BudgetV1(
            range_id=uuid.uuid4(),
            max_total_cost_usd=0,
            max_duration_seconds=3600,
        )


# ---------------------------------------------------------------------------
# TargetRef
# ---------------------------------------------------------------------------


def test_target_ref_accepts_bare_host_or_ip():
    ref = TargetRef(range_id=uuid.uuid4(), host_or_ip="10.20.0.5")
    assert ref.host_or_ip == "10.20.0.5"


@pytest.mark.parametrize(
    "bad_value",
    [
        "http://10.20.0.5/",  # scheme + path, not a bare host
        "10.20.0.5; rm -rf /",  # shell metacharacter injection attempt
        "10.20.0.5 extra",  # whitespace
        "",
    ],
)
def test_target_ref_rejects_injection_shaped_text(bad_value):
    with pytest.raises(ValidationError):
        TargetRef(range_id=uuid.uuid4(), host_or_ip=bad_value)


# ---------------------------------------------------------------------------
# RangeOwnershipTokenV1
# ---------------------------------------------------------------------------


def test_range_ownership_token_constructs_and_reports_expiry():
    range_id = uuid.uuid4()
    ref = TargetRef(range_id=range_id, host_or_ip="10.20.0.5")
    token = RangeOwnershipTokenV1(
        world_id=uuid.uuid4(),
        range_id=range_id,
        target_set=[ref],
        capabilities=[AbilityCategory.RECON],
        expires_at=_now() + timedelta(minutes=5),
        issuer_signature="deadbeef",
    )
    assert token.is_expired is False

    expired_token = token.model_copy(update={"expires_at": _now() - timedelta(seconds=1)})
    assert expired_token.is_expired is True


def test_range_ownership_token_rejects_expiry_before_issuance():
    range_id = uuid.uuid4()
    with pytest.raises(ValidationError):
        RangeOwnershipTokenV1(
            world_id=uuid.uuid4(),
            range_id=range_id,
            issued_at=_now(),
            expires_at=_now() - timedelta(minutes=5),
            issuer_signature="deadbeef",
        )


# ---------------------------------------------------------------------------
# ExecutionRequestV1
# ---------------------------------------------------------------------------


def _make_request(**overrides):
    range_id = overrides.pop("range_id", uuid.uuid4())
    ref = overrides.pop("target_ref", TargetRef(range_id=range_id, host_or_ip="10.20.0.5"))
    defaults = dict(
        task_id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        range_id=range_id,
        target_refs=[ref],
        action_category=AbilityCategory.RECON,
        ability_ref="attack.discovery.host",
        requested_by="agent-tool-call-1",
    )
    defaults.update(overrides)
    return ExecutionRequestV1(**defaults)


def test_execution_request_constructs():
    req = _make_request()
    assert req.action_category is AbilityCategory.RECON


def test_execution_request_rejects_target_like_param_keys():
    with pytest.raises(ValidationError):
        _make_request(params={"host": "attacker.example.com"})


def test_execution_request_rejects_target_ref_from_a_different_range():
    other_range_ref = TargetRef(range_id=uuid.uuid4(), host_or_ip="10.99.0.1")
    with pytest.raises(ValidationError):
        _make_request(target_refs=[other_range_ref])


def test_execution_request_rejects_empty_target_refs():
    with pytest.raises(ValidationError):
        _make_request(target_refs=[])


# ---------------------------------------------------------------------------
# ExecutionTicketV1 / PolicyDecisionV1
# ---------------------------------------------------------------------------


def _make_ticket(request_hash="abc123"):
    return ExecutionTicketV1(
        request_hash=request_hash,
        expires_at=_now() + timedelta(seconds=60),
        signature="deadbeef",
    )


def test_policy_decision_allow_requires_ticket():
    with pytest.raises(ValidationError):
        PolicyDecisionV1(allowed=True, request_hash="abc123", ticket=None)


def test_policy_decision_allow_with_ticket_is_valid():
    decision = PolicyDecisionV1(allowed=True, request_hash="abc123", ticket=_make_ticket())
    assert decision.allowed is True
    assert decision.reason is None


def test_policy_decision_deny_requires_reason():
    with pytest.raises(ValidationError):
        PolicyDecisionV1(allowed=False, request_hash="abc123", ticket=None)


def test_policy_decision_deny_rejects_ticket():
    with pytest.raises(ValidationError):
        PolicyDecisionV1(
            allowed=False,
            reason=PolicyDenyReason.TARGET_NOT_IN_RANGE,
            request_hash="abc123",
            ticket=_make_ticket(),
        )


# ---------------------------------------------------------------------------
# AuditRecordV1
# ---------------------------------------------------------------------------


def test_audit_record_deny_requires_reason():
    with pytest.raises(ValidationError):
        AuditRecordV1(
            seq=0,
            prev_hash="0" * 64,
            actor=ActorRef(kind=PolicyActorKind.AGENT, id="agent-1"),
            request_hash="abc123",
            decision="DENY",
            world_id=uuid.uuid4(),
            provenance=ProvenanceRef(package="ghostrange_policy_check", version="0.1.0"),
            signature="deadbeef",
        )


def test_audit_record_allow_constructs():
    record = AuditRecordV1(
        seq=0,
        prev_hash="0" * 64,
        actor=ActorRef(kind=PolicyActorKind.SERVICE, id="range-runtime"),
        request_hash="abc123",
        decision="ALLOW",
        world_id=uuid.uuid4(),
        provenance=ProvenanceRef(package="ghostrange_policy_check", version="0.1.0"),
        signature="deadbeef",
    )
    assert record.decision == "ALLOW"
