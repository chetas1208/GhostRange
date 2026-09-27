"""Security matrix — production boundary and approval abuse."""

from __future__ import annotations

import uuid

import pytest

from ghostrange_ghostgate.boundary import ProductionBoundaryGuard
from ghostrange_ghostgate.promote import GhostGate, PromotionPrepareInput


@pytest.mark.parametrize(
    "text",
    [
        "kubectl apply -f prod.yaml",
        "tofu apply",
        "ssh root@prod.example.com",
    ],
)
def test_forbidden_patterns_detected(text: str):
    hits = ProductionBoundaryGuard.scan_text(text)
    assert hits


def test_counterexample_blocks_promotion():
    from ghostrange_contracts.adversarial_m8 import (
        AdversarialBudgetV1,
        AdversarialClaimPhase,
        AdversarialVerificationReportV1,
        CounterexampleV1,
        SearchArmKind,
        SearchPolicyId,
        SearchStopReason,
    )

    gate = GhostGate()
    cid = uuid.uuid4()
    budget = AdversarialBudgetV1(max_attempts=10)
    cx = CounterexampleV1(
        claim_id=cid,
        world_id=uuid.uuid4(),
        search_run_id=uuid.uuid4(),
        action_sequence=[{"method": "GET", "path": "/admin"}],
        violated_invariant="no_admin_bypass",
        claim_contradiction="admin reachable",
        discovered_by=SearchArmKind.HEADER_MUTATION,
        search_strategy=SearchPolicyId.UNIFORM_RANDOM,
        search_budget_snapshot=budget,
    )
    adv = AdversarialVerificationReportV1(
        claim_id=cid,
        search_run_id=uuid.uuid4(),
        phase=AdversarialClaimPhase.COUNTEREXAMPLE_FOUND,
        budget=budget,
        search_policy=SearchPolicyId.UNIFORM_RANDOM,
        counterexamples=[cx],
        stop_reason=SearchStopReason.COUNTEREXAMPLE_CONFIRMED,
    )
    res = gate.prepare(
        PromotionPrepareInput(
            experiment_id=uuid.uuid4(),
            remediation_id=uuid.uuid4(),
            source_revision_id=uuid.uuid4(),
            twin_revision_id=uuid.uuid4(),
            evidence_root_digest="x",
            adversarial=adv,
        )
    )
    assert "COUNTEREXAMPLE_FOUND" in res.candidate.readiness.blockers
