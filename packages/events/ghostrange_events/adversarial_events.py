"""M8 adversarial search domain events (low-volume)."""

ADVERSARIAL_SEARCH_STARTED = "adversarial.search_started"
ADVERSARIAL_SEARCH_STOPPED = "adversarial.search_stopped"
SEARCH_CANDIDATE_REJECTED = "search.candidate_rejected"
SEARCH_CANDIDATE_EXECUTED = "search.candidate_executed"
COUNTEREXAMPLE_CANDIDATE_FOUND = "counterexample.candidate_found"
COUNTEREXAMPLE_CONFIRMED = "counterexample.confirmed"
COUNTEREXAMPLE_REJECTED = "counterexample.rejected"
CLAIM_COUNTEREXAMPLE_FOUND = "claim.counterexample_found"
CLAIM_SURVIVED_SEARCH_BUDGET = "claim.survived_search_budget"
REMEDIATION_REVISION_CREATED = "remediation.revision_created"
VERIFICATION_SUITE_COUNTEREXAMPLE_ADDED = "verification_suite.counterexample_added"

__all__ = [
    "ADVERSARIAL_SEARCH_STARTED",
    "ADVERSARIAL_SEARCH_STOPPED",
    "SEARCH_CANDIDATE_REJECTED",
    "SEARCH_CANDIDATE_EXECUTED",
    "COUNTEREXAMPLE_CANDIDATE_FOUND",
    "COUNTEREXAMPLE_CONFIRMED",
    "COUNTEREXAMPLE_REJECTED",
    "CLAIM_COUNTEREXAMPLE_FOUND",
    "CLAIM_SURVIVED_SEARCH_BUDGET",
    "REMEDIATION_REVISION_CREATED",
    "VERIFICATION_SUITE_COUNTEREXAMPLE_ADDED",
]
