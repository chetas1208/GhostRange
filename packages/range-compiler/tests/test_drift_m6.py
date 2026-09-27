from pathlib import Path
from uuid import uuid4

from ghostrange_contracts.living_twin_m6 import ClaimValidityStatus, SyncDecision
from ghostrange_range_compiler.drift import analyze_revisions

ROOT = Path(__file__).resolve().parents[3]
FIX = ROOT / "tests" / "fixtures" / "drift"
AUTH_A = FIX / "auth-v24" / "docker-compose.yml"
AUTH_B = FIX / "auth-v27" / "docker-compose.yml"
AUTH_LAB = ROOT / "ranges" / "ghostrange-auth-lab-v1" / "docker" / "vm-1" / "docker-compose.yml"


def test_no_drift_same_file():
    a = analyze_revisions(AUTH_LAB, AUTH_LAB, claim_ids=[uuid4()])
    assert a.drift.formatting_only is True
    assert a.sync_decision == SyncDecision.IGNORE
    assert a.claim_updates[0].status == ClaimValidityStatus.CURRENT


def test_auth_version_drift_stales_claim():
    cid = uuid4()
    a = analyze_revisions(AUTH_A, AUTH_B, claim_ids=[cid])
    assert not a.drift.formatting_only
    assert any("auth" in ev.entity_name for ev in a.drift.events)
    assert a.revalidation is not None
    assert cid in (a.revalidation.claims_awaiting or [])
    stale = [u for u in a.claim_updates if u.claim_id == cid][0]
    assert stale.status == ClaimValidityStatus.STALE


def test_revalidation_includes_auth_tests():
    a = analyze_revisions(AUTH_A, AUTH_B, claim_ids=[uuid4()])
    assert "attack_replay" in (a.revalidation.verification_tests if a.revalidation else [])
