"""Agent 04 — auth bypass variable ontology."""

from ghostrange_contracts.ghostcausal_m14 import CausalVariableCategory, CausalVariableV1

AUTH_BYPASS_VARIABLES: list[CausalVariableV1] = [
    CausalVariableV1(variable_id="V_REFRESH", name="SESSION_REFRESH", category=CausalVariableCategory.SESSION_STATE),
    CausalVariableV1(variable_id="V_CACHE", name="STALE_CACHE", category=CausalVariableCategory.CACHE_STATE),
    CausalVariableV1(variable_id="V_IDENTITY", name="STALE_IDENTITY", category=CausalVariableCategory.IDENTITY_STATE),
    CausalVariableV1(variable_id="V_ROUTE", name="GATEWAY_ROUTE", category=CausalVariableCategory.NETWORK_POLICY),
    CausalVariableV1(variable_id="V_TIMING", name="REQUEST_TIMING", category=CausalVariableCategory.REQUEST_ORDER),
    CausalVariableV1(
        variable_id="V_BYPASS",
        name="AUTHORIZATION_BYPASS",
        category=CausalVariableCategory.SECURITY_OUTCOME,
    ),
]
