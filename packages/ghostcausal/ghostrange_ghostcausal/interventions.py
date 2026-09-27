"""Agents 13–14 — interventions and compiler."""

from __future__ import annotations

from ghostrange_contracts.ghostcausal_m14 import CausalInterventionV1

from .simulator import InterventionKind


def propose_discrimination_interventions() -> list[CausalInterventionV1]:
    return [
        CausalInterventionV1(
            variable_id="V_CTRL",
            action="observe_baseline",
            world_label=InterventionKind.CONTROL.value,
            expected_mechanism="baseline",
            cost_usd_estimate=0.4,
        ),
        CausalInterventionV1(
            variable_id="V_CACHE",
            action="do(cache=clean)",
            world_label=InterventionKind.CACHE_INVALIDATED.value,
            expected_mechanism="break stale identity chain",
            cost_usd_estimate=0.5,
        ),
        CausalInterventionV1(
            variable_id="V_ROUTE",
            action="do(route=alt)",
            world_label=InterventionKind.ROUTE_CHANGED.value,
            expected_mechanism="test routing hypothesis",
            cost_usd_estimate=0.5,
        ),
    ]


def compile_intervention(intervention: CausalInterventionV1) -> dict:
    """Range-bound operation — no shell."""
    return {
        "typed_op": "RANGE_CONFIG_CHANGE",
        "variable": intervention.variable_id,
        "action": intervention.action,
        "world": intervention.world_label,
        "scope": intervention.scope,
    }
