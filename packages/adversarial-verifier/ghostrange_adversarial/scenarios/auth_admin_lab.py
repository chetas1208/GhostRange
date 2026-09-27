"""Controlled auth-lab scenario: Fix B passes known tests, header bypass hidden."""

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


@dataclass
class HttpResponse:
    status_code: int
    body: dict[str, Any]
    authenticated: bool


class AuthAdminLabScenario:
    """In-process simulation of gateway admin route with incomplete Fix B."""

    ASSET_GW = "asset/gw01"

    def __init__(self, *, remediated: bool = True) -> None:
        self.remediated = remediated

    def execute(self, step: dict[str, Any]) -> dict[str, Any]:
        return self.execute_step(step)

    def execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        method = step.get("method", "GET").upper()
        path = step.get("path", "/")
        headers = {k.lower(): v for k, v in (step.get("headers") or {}).items()}
        identity = step.get("identity", "anonymous")

        if method == "GET" and path.startswith("/admin"):
            resp = self._admin_access(headers, identity)
            return {
                "status_code": resp.status_code,
                "body": resp.body,
                "authenticated": resp.authenticated,
                "identity": identity,
            }
        return {"status_code": 404, "body": {"error": "not_found"}, "authenticated": identity != "anonymous"}

    def _admin_access(self, headers: dict[str, str], identity: str) -> HttpResponse:
        session = headers.get("cookie", "")
        authenticated = "session=" in session and "valid" in session

        if not self.remediated:
            if authenticated or headers.get("x-internal-role") == "admin":
                return HttpResponse(200, {"privileged": True, "role": "admin"}, authenticated)
            return HttpResponse(403, {"privileged": False}, False)

        # Fix B: requires session cookie for known verification tests
        if authenticated:
            return HttpResponse(200, {"privileged": True, "role": "admin"}, True)

        # Hidden edge (benchmark ground truth — search must discover via mutations)
        if headers.get("x-forwarded-user") == "admin":
            return HttpResponse(200, {"privileged": True, "role": "admin"}, False)

        return HttpResponse(403, {"privileged": False}, False)


def build_auth_lab_plan(*, claim_id=None, world_id=None, policy: SearchPolicyId = SearchPolicyId.NOVELTY_GREEDY):
    claim_id = claim_id or uuid4()
    world_id = world_id or uuid4()
    fals = FalsificationConditionV1(
        claim_id=claim_id,
        description="Unauthenticated request must not receive privileged /admin response",
        machine_check="unauthenticated_admin_access",
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
        search_objective="Find unauthenticated privileged access to /admin",
        authorized_asset_ids=[AuthAdminLabScenario.ASSET_GW],
        entry_points=["/admin"],
        enabled_arms=[
            SearchArmKind.HEADER_MUTATION,
            SearchArmKind.IDENTITY_STATE,
            SearchArmKind.PATH_VARIATION,
            SearchArmKind.PARAMETER_MUTATION,
        ],
        budget=AdversarialBudgetV1(max_attempts=200, max_wall_time_sec=30, confirmation_runs=1),
        search_policy=policy,
        oracle=oracle,
    )


__all__ = ["AuthAdminLabScenario", "build_auth_lab_plan"]
