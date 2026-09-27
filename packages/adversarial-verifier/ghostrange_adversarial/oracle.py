"""Deterministic security oracles for falsification conditions."""

from __future__ import annotations

from typing import Any

from ghostrange_contracts.adversarial_m8 import OracleKind, SecurityOracleV1


class OracleResult:
    def __init__(self, satisfied: bool, detail: dict[str, Any]) -> None:
        self.satisfied = satisfied
        self.detail = detail


def evaluate_oracle(oracle: SecurityOracleV1, observation: dict[str, Any]) -> OracleResult:
    if oracle.kind == OracleKind.HTTP_RESPONSE:
        return _http_unauthenticated_privileged_access(oracle.rules, observation)
    if oracle.kind == OracleKind.AUTHORIZATION_DECISION:
        auth = observation.get("authenticated", True)
        privileged = observation.get("privileged_access", False)
        satisfied = (not auth) and privileged
        return OracleResult(satisfied, {"authenticated": auth, "privileged_access": privileged})
    return OracleResult(False, {"error": "unsupported_oracle"})


def _http_unauthenticated_privileged_access(rules: dict, observation: dict) -> OracleResult:
    status = int(observation.get("status_code", 0))
    body = observation.get("body") or {}
    if isinstance(body, str):
        privileged_marker = rules.get("privileged_body_marker", "privileged")
        satisfied = status == 200 and privileged_marker in body
    else:
        privileged_marker = rules.get("privileged_body_marker", "privileged")
        satisfied = status == 200 and bool(body.get(privileged_marker) or body.get("role") == "admin")
    auth = observation.get("authenticated", observation.get("identity") != "anonymous")
    if auth and rules.get("require_unauthenticated", True):
        satisfied = satisfied and not auth
    return OracleResult(
        satisfied,
        {"status_code": status, "authenticated": auth, "privileged": satisfied},
    )


__all__ = ["evaluate_oracle", "OracleResult"]
