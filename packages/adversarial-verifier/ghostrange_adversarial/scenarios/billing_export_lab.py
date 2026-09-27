"""Golden-path adversarial scenario #2: cross-tenant billing export, shallow fix vs. deep fix.

Companion to ``ghostrange_director.scenarios.tenant_escalation`` (the M9 investigation side of
the same incident). This module is the M8 side: an in-process simulation of the billing-service
``/billing/export`` endpoint with two independently-checkable remediation candidates, built so
that a genuinely shallow fix gets falsified and a genuinely deeper fix survives the same search
— the "try to break the fix" step that is the whole point of GhostRange's adversarial verifier.

Ground truth (three states, selected by ``fix=``):

  "none"           — no fix. The endpoint trusts ``X-Internal-Role: admin`` unconditionally
                      (the config-drift bug from the investigation side) *and* a second,
                      unrelated legacy header, ``X-Debug-Auth: bypass``, left over from an old
                      debugging tool integration nobody remembered.
  "fix_a_shallow"  — the fix a reasonable engineer ships first: it strips/ignores
                      ``X-Internal-Role`` (the header everyone found first), but nobody knew
                      about ``X-Debug-Auth`` — so it's still honored. The mutation search's
                      header arm tries every header in ``mutations.HEADER_CANDIDATES``
                      (a fixed, shared list — see note below) and finds ``X-Debug-Auth:
                      bypass`` still grants privileged cross-tenant access. FALSIFIED.
  "fix_b_deep"     — removes *all* header-based trust and only grants access when the caller's
                      own session is valid for the tenant being requested. No header/path/
                      identity mutation in the fixed candidate universe reproduces privileged
                      access. SURVIVES the budget.

Deliberately reuses the *existing*, unmodified ``ghostrange_adversarial.mutations`` candidate
generator rather than inventing new header names: ``HEADER_CANDIDATES`` is a fixed list shared
with the auth_admin_lab scenario and asserted on by seeded-random tests
(``test_adversarial.py::test_benchmark_ground_truth_alignment``), so changing it would silently
change what those tests find. ``X-Debug-Auth`` is already in that list — this scenario's
"the shallow fix misses a second header" story is built entirely out of headers the generator
already tries, which also means it is a scenario that was actually exercised, not merely
plausible on paper. ``SearchArmKind.PARAMETER_MUTATION`` is listed in ``enabled_arms`` for
parity with the M8 plan shape, but note ``mutations.generate_candidates`` currently has no
branch for it (a real, pre-existing stub) — it contributes zero candidates and is harmless to
list, but nothing here depends on it firing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from ghostrange_contracts.adversarial_m8 import (
    AdversarialBudgetV1,
    AdversarialSearchPlanV1,
    FalsificationConditionV1,
    OracleKind,
    SearchArmKind,
    SearchPolicyId,
    SecurityOracleV1,
)

FIX_NONE = "none"
FIX_A_SHALLOW = "fix_a_shallow"
FIX_B_DEEP = "fix_b_deep"


@dataclass
class HttpResponse:
    status_code: int
    body: dict[str, Any]
    authenticated: bool


class BillingTenantExportScenario:
    """In-process simulation of ``GET /billing/export`` under three remediation states."""

    ASSET_BILLING = "asset/billing01"

    def __init__(self, *, fix: str = FIX_B_DEEP) -> None:
        if fix not in (FIX_NONE, FIX_A_SHALLOW, FIX_B_DEEP):
            raise ValueError(f"unknown fix state: {fix}")
        self.fix = fix

    def execute(self, step: dict[str, Any]) -> dict[str, Any]:
        return self.execute_step(step)

    def execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        method = step.get("method", "GET").upper()
        path = step.get("path", "/")
        headers = {k.lower(): v for k, v in (step.get("headers") or {}).items()}
        identity = step.get("identity", "anonymous")

        if method == "GET" and path.startswith("/billing/export"):
            resp = self._export_access(headers, identity)
            return {
                "status_code": resp.status_code,
                "body": resp.body,
                "authenticated": resp.authenticated,
                "identity": identity,
            }
        return {"status_code": 404, "body": {"error": "not_found"}, "authenticated": identity != "anonymous"}

    def _export_access(self, headers: dict[str, str], identity: str) -> HttpResponse:
        session = headers.get("cookie", "")
        authenticated = "session=" in session and "valid" in session

        # Legitimate path: authenticated caller sees only their own tenant's export — never
        # "privileged"/cross-tenant, regardless of remediation state.
        if authenticated:
            return HttpResponse(200, {"privileged": False, "scope": "own_tenant"}, True)

        # Config-drift vector: leftover internal-role trust (the investigation side's hidden
        # mechanism). Closed by both fixes.
        if self.fix == FIX_NONE and headers.get("x-internal-role") == "admin":
            return HttpResponse(200, {"privileged": True, "scope": "cross_tenant", "role": "admin"}, False)

        # Second, independent vector: legacy debug-bypass header. The shallow fix never learned
        # about this one — only the deep fix closes it.
        if self.fix in (FIX_NONE, FIX_A_SHALLOW) and headers.get("x-debug-auth") == "bypass":
            return HttpResponse(200, {"privileged": True, "scope": "cross_tenant", "role": "debug-admin"}, False)

        return HttpResponse(403, {"privileged": False}, False)


def build_billing_export_lab_plan(
    *,
    claim_id=None,
    world_id=None,
    policy: SearchPolicyId = SearchPolicyId.NOVELTY_GREEDY,
) -> AdversarialSearchPlanV1:
    claim_id = claim_id or uuid4()
    world_id = world_id or uuid4()
    fals = FalsificationConditionV1(
        claim_id=claim_id,
        description="Unauthenticated request must not receive privileged cross-tenant billing export",
        machine_check="unauthenticated_cross_tenant_billing_access",
        required_observations=["status_code", "privileged", "authenticated"],
    )
    oracle = SecurityOracleV1(
        kind=OracleKind.HTTP_RESPONSE,
        falsification_condition_id=fals.id,
        rules={"privileged_body_marker": "privileged", "require_unauthenticated": True},
    )
    return AdversarialSearchPlanV1(
        claim_id=claim_id,
        world_id=world_id,
        falsification_condition=fals,
        search_objective="Find unauthenticated privileged cross-tenant access to /billing/export",
        authorized_asset_ids=[BillingTenantExportScenario.ASSET_BILLING],
        entry_points=["/billing/export"],
        enabled_arms=[
            SearchArmKind.HEADER_MUTATION,
            SearchArmKind.IDENTITY_STATE,
            SearchArmKind.PATH_VARIATION,
            SearchArmKind.PARAMETER_MUTATION,
        ],
        # max_parallel_searches raised from the M8 default (4) to reflect this golden path's
        # two independently-verifiable remediation candidates (shallow + deep), each its own
        # search world — sized for, not padded to, a live run that can afford more than one
        # concurrent real worker. Purely descriptive: engine.py's search loop itself is
        # single-world per call; parallelism across worlds is the caller's (golden_path's).
        budget=AdversarialBudgetV1(max_attempts=200, max_wall_time_sec=30, confirmation_runs=1, max_parallel_searches=6),
        search_policy=policy,
        oracle=oracle,
    )


__all__ = [
    "BillingTenantExportScenario",
    "build_billing_export_lab_plan",
    "FIX_NONE",
    "FIX_A_SHALLOW",
    "FIX_B_DEEP",
]
