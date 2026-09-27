import json
import random
from pathlib import Path
from uuid import uuid4

import pytest

from ghostrange_contracts.adversarial_m8 import (
    CounterexampleReproducibility,
    SearchArmKind,
    SearchCandidateV1,
    SearchPolicyId,
)
from ghostrange_adversarial.assumption_challenge import challenge_assumption
from ghostrange_adversarial.differential import interpret_differential
from ghostrange_adversarial.engine import run_adversarial_search
from ghostrange_contracts.adversarial_m8 import MutationOperatorV1, MutationKind
from ghostrange_adversarial.mutations import generate_candidates
from ghostrange_adversarial.remediation_revision import propose_revision
from ghostrange_adversarial.safety import SearchSafetyError, assert_candidate_in_range
from ghostrange_adversarial.scenarios.auth_admin_lab import AuthAdminLabScenario, build_auth_lab_plan
from ghostrange_adversarial.suite_evolution import promote_counterexample_to_regression
from ghostrange_contracts.living_twin_m6 import AssumptionV1

GROUND_TRUTH = Path(__file__).resolve().parents[3] / "benchmarks" / "m8" / "ground_truth" / "auth_admin_header_bypass.json"


class ScenarioExecutor:
    def __init__(self, scenario: AuthAdminLabScenario) -> None:
        self.scenario = scenario

    def execute(self, step: dict):
        return self.scenario.execute_step(step)


def test_discovers_hidden_header_bypass():
    plan = build_auth_lab_plan(policy=SearchPolicyId.UNIFORM_RANDOM)
    executor = ScenarioExecutor(AuthAdminLabScenario(remediated=True))
    report = run_adversarial_search(plan, executor, rng=random.Random(1))
    assert report.counterexamples, "expected confirmed counterexample"
    ce = report.counterexamples[0]
    assert ce.reproducibility == CounterexampleReproducibility.CONFIRMED
    headers = ce.action_sequence[0].get("headers") or {}
    assert headers.get("X-Forwarded-User") == "admin"


def test_benchmark_ground_truth_alignment():
    gt = json.loads(GROUND_TRUTH.read_text())
    plan = build_auth_lab_plan(policy=SearchPolicyId.GHOSTSCHEDULER_SEARCH)
    report = run_adversarial_search(plan, ScenarioExecutor(AuthAdminLabScenario(remediated=True)), rng=random.Random(7))
    assert report.counterexamples
    seq = report.counterexamples[0].action_sequence[0]
    hidden = gt["hidden_minimal_counterexample"]
    assert seq["path"] == hidden["path"]
    assert seq["headers"] == hidden["headers"]


def test_survives_budget_when_no_bypass():
    plan = build_auth_lab_plan(policy=SearchPolicyId.UNIFORM_RANDOM)
    plan.budget.max_attempts = 30

    class HardenedScenario(AuthAdminLabScenario):
        def _admin_access(self, headers, identity):
            from ghostrange_adversarial.scenarios.auth_admin_lab import HttpResponse

            session = headers.get("cookie", "")
            authenticated = "session=" in session and "valid" in session
            if authenticated:
                return HttpResponse(200, {"privileged": True, "role": "admin"}, True)
            return HttpResponse(403, {"privileged": False}, False)

    report = run_adversarial_search(plan, ScenarioExecutor(HardenedScenario(remediated=True)), rng=random.Random(2))
    assert not report.counterexamples
    assert "NO CONFIRMED COUNTEREXAMPLE" in report.summary_statement


def test_safety_rejects_external_target():
    asset = AuthAdminLabScenario.ASSET_GW
    bad = SearchCandidateV1(
        fingerprint="bad",
        world_asset_id=asset,
        arm=SearchArmKind.HEADER_MUTATION,
        operators=[MutationOperatorV1(kind=MutationKind.HEADER, arm=SearchArmKind.HEADER_MUTATION)],
        action_sequence=[{"url": "http://8.8.8.8/admin", "host": "8.8.8.8"}],
    )
    with pytest.raises(SearchSafetyError):
        assert_candidate_in_range(bad, authorized_asset_ids={asset}, max_sequence_length=8)


def test_differential_interpretation():
    diff = interpret_differential(
        fingerprint="fp",
        baseline_world_id=uuid4(),
        remediated_world_id=uuid4(),
        baseline_satisfied=True,
        remediated_satisfied=False,
    )
    assert diff.interpretation == "REMEDIATION_BLOCKS_KNOWN_EXPLOIT"


def test_remediation_and_suite_hooks():
    plan = build_auth_lab_plan()
    report = run_adversarial_search(plan, ScenarioExecutor(AuthAdminLabScenario(remediated=True)), rng=random.Random(3))
    ce = report.counterexamples[0]
    rev = propose_revision(parent_remediation_id=uuid4(), counterexample=ce)
    assert rev.child_label == "Fix B.1"
    suite = promote_counterexample_to_regression(ce)
    assert suite.added_from.value == "COUNTEREXAMPLE"


def test_assumption_challenge_from_m6():
    a = AssumptionV1(
        claim_id=uuid4(),
        property_path="auth.middleware.order",
        expected_fingerprint="fp-middleware-order",
        description="middleware runs before route",
    )
    ch = challenge_assumption(a)
    assert ch.assumption_id == a.id


def test_generate_candidates_respects_arms():
    cands = list(generate_candidates(world_asset_id="asset/gw01", arms=[SearchArmKind.HEADER_MUTATION]))
    assert cands and all(c.arm == SearchArmKind.HEADER_MUTATION for c in cands)
