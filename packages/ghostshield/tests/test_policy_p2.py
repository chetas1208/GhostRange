from uuid import uuid4

from ghostrange_contracts.ghostshield_m17 import (
    AuthorizationContextV1,
    AuthorizationVerdict,
    CanonicalActionType,
    CanonicalActionV1,
    GhostShieldMode,
)
from ghostrange_ghostshield import GhostExecutionGateway, GhostShieldPolicyEngine


def _ctx(**kw):
    defaults = dict(
        campaign_id=uuid4(),
        runtime_revision=1,
        active_workers=1,
        max_active_workers=1,
        budget_spent_usd=0.0,
        budget_hard_cap_usd=25.0,
        safe_mode=False,
    )
    defaults.update(kw)
    return AuthorizationContextV1(**defaults)


def test_p2_denies_second_worker_create():
    engine = GhostShieldPolicyEngine()
    cid = uuid4()
    action = CanonicalActionV1(
        action_type=CanonicalActionType.CREATE_WORKER,
        principal="ghostscheduler",
        campaign_id=cid,
        target="worker-slot",
        parameters={"plan": "vc2-1c-1gb"},
        state_revision=1,
        idempotency_key="create-2",
    )
    verdict = engine.evaluate(action, _ctx(campaign_id=cid))
    assert verdict.verdict == AuthorizationVerdict.DENY
    assert "P2_MAX_ACTIVE_WORKERS" in verdict.reason_codes


def test_enforce_blocks_denied_effect():
    gw = GhostExecutionGateway(mode=GhostShieldMode.ENFORCE)
    cid = uuid4()
    action = CanonicalActionV1(
        action_type=CanonicalActionType.CREATE_WORKER,
        principal="ghostscheduler",
        campaign_id=cid,
        target="w",
        parameters={},
        state_revision=1,
        idempotency_key="x",
    )
    ctx = _ctx(campaign_id=cid)
    try:
        gw.execute_protected(
            action=action,
            ctx=ctx,
            permit=None,
            effect=lambda: "should-not-run",
        )
        assert False, "expected GatewayError"
    except Exception as exc:
        assert "DENY" in str(exc)


def test_toctou_stale_revision():
    engine = GhostShieldPolicyEngine()
    cid = uuid4()
    action = CanonicalActionV1(
        action_type=CanonicalActionType.CREATE_WORKER,
        principal="ghostscheduler",
        campaign_id=cid,
        target="w",
        parameters={},
        state_revision=1,
        idempotency_key="x",
    )
    verdict = engine.evaluate(action, _ctx(campaign_id=cid, active_workers=0, runtime_revision=2))
    assert verdict.verdict == AuthorizationVerdict.STATE_STALE
