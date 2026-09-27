from uuid import uuid4

from ghostrange_contracts.ghostruntime_m16 import CampaignRuntimeState, RecoveryAction, SideEffectStatus
from ghostrange_ghostruntime.recovery import CampaignRecoveryManager, RecoveryContext


def test_unknown_create_adopts_when_provider_reports_worker():
    cid = uuid4()
    mgr = CampaignRecoveryManager()
    decision = mgr.decide(
        RecoveryContext(
            campaign_id=cid,
            lifecycle=CampaignRuntimeState.RECOVERING,
            unknown_effects=["create-worker-1"],
            provider_workers_observed=["vultr-instance-abc"],
            provider_workers_expected=[],
            budget_hard_cap_usd=10.0,
        )
    )
    assert decision.action == RecoveryAction.RESUME
    assert "ADOPT_EXISTING_WORKER" in decision.reason_codes


def test_unknown_create_enters_safe_mode_without_provider_worker():
    cid = uuid4()
    mgr = CampaignRecoveryManager()
    decision = mgr.decide(
        RecoveryContext(
            campaign_id=cid,
            lifecycle=CampaignRuntimeState.RECOVERING,
            unknown_effects=["create-worker-1"],
            provider_workers_observed=[],
            budget_hard_cap_usd=10.0,
        )
    )
    assert decision.action == RecoveryAction.SAFE_MODE


def test_reconcile_unknown_create_completed_when_observed():
    mgr = CampaignRecoveryManager()
    status, codes = mgr.reconcile_unknown_create(observed_provider_id="inst-1")
    assert status == SideEffectStatus.COMPLETED
    assert "ADOPT_EXISTING_WORKER" in codes
