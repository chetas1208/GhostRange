from uuid import uuid4

from ghostrange_contracts.adversarial_m8 import (
    AdversarialVerificationReportV1,
    AdversarialBudgetV1,
    SearchStopReason,
    AdversarialClaimPhase,
    SearchPolicyId,
)


def test_report_honest_summary_on_budget_exhaust():
    r = AdversarialVerificationReportV1(
        claim_id=uuid4(),
        search_run_id=uuid4(),
        phase=AdversarialClaimPhase.SURVIVED_BUDGET,
        budget=AdversarialBudgetV1(),
        search_policy=SearchPolicyId.UNIFORM_RANDOM,
        attempts=10,
        stop_reason=SearchStopReason.BUDGET_EXHAUSTED,
    )
    assert "NO CONFIRMED COUNTEREXAMPLE" in r.summary_statement
