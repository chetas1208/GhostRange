"""The one exception type callers of authorize() need to know about.

Deliberately a single, narrow exception class: every deny path in
``service.py`` (expected policy violation *or* unexpected internal error)
raises this and only this. A caller that does not explicitly catch
``PolicyDenied`` gets a hard crash, not a silently-ignored ``False`` return
value that a lazy call site could `if decision:` past — see
docs/security/EXECUTION_POLICY.md §3.2 ("this is a hard fail, not a
warning") and §3.3 (fail-closed default).
"""

from __future__ import annotations

from ghostrange_contracts.policy import PolicyDecisionV1


class PolicyDenied(Exception):
    """Raised by ``PolicyCheckService.authorize()`` on any deny outcome.

    Callers (execution-graph, adversary-adapter, range-runtime,
    vultr-control) MUST catch this and treat it as a hard, terminal
    failure for the task node it was raised for: no retry with different
    wording, no fallback to a degraded execution path, no re-attempt under
    a different task_id without going through ``authorize()`` again.

    ``decision`` carries the structured, already-audited
    ``PolicyDecisionV1(allowed=False, reason=...)`` for logging/telemetry.
    """

    def __init__(self, decision: PolicyDecisionV1):
        if decision.allowed:
            raise ValueError("PolicyDenied must be constructed from a DENY decision")
        self.decision = decision
        super().__init__(f"policy denied: {decision.reason}")


__all__ = ["PolicyDenied"]
