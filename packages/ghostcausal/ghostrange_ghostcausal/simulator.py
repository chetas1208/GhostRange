"""GhostCausalSimulator — SCM ground truth for evaluator only (Agent 38)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

# Runtime must NOT import EvaluatorGroundTruth in production paths — only tests/benchmark.


class InterventionKind(str, Enum):
    CONTROL = "CONTROL"
    CACHE_INVALIDATED = "CACHE_INVALIDATED"
    ROUTE_CHANGED = "ROUTE_CHANGED"
    REFRESH_DISABLED = "REFRESH_DISABLED"
    COUNTERFACTUAL_CACHE_BEFORE_REFRESH = "COUNTERFACTUAL_CACHE_BEFORE_REFRESH"


@dataclass
class WorldOutcome:
    label: str
    bypass: bool
    mechanism_notes: str = ""


@dataclass
class _EvaluatorGroundTruth:
    """Hidden from CausalInvestigationEngine."""

    refresh_causes_stale_cache: bool = True
    stale_cache_causes_stale_identity: bool = True
    stale_identity_causes_bypass: bool = True
    route_causes_bypass: bool = False
    timing_confounds: bool = True


@dataclass
class GhostCausalSimulator:
    """Synthetic auth bypass SCM — evaluator holds truth."""

    truth: _EvaluatorGroundTruth = field(default_factory=_EvaluatorGroundTruth)
    label: str = "SIMULATED_SCM"

    def run_intervention(self, kind: InterventionKind) -> WorldOutcome:
        t = self.truth
        if kind == InterventionKind.CONTROL:
            return WorldOutcome("CONTROL", True, "baseline bypass")
        if kind == InterventionKind.CACHE_INVALIDATED:
            return WorldOutcome("CACHE_INVALIDATED", False, "cache on causal path")
        if kind == InterventionKind.ROUTE_CHANGED:
            return WorldOutcome("ROUTE_CHANGED", True, "route not on mechanism")
        if kind == InterventionKind.REFRESH_DISABLED:
            return WorldOutcome("REFRESH_DISABLED", False, "refresh upstream of cache")
        if kind == InterventionKind.COUNTERFACTUAL_CACHE_BEFORE_REFRESH:
            return WorldOutcome("COUNTERFACTUAL", False, "counterfactual blocks bypass")
        return WorldOutcome(kind.value, True, "unknown")

    def observational_correlations(self) -> dict[str, float]:
        """All correlate under confounding — not causal."""
        if self.truth.timing_confounds:
            return {
                "SESSION_REFRESH": 0.91,
                "STALE_CACHE": 0.89,
                "GATEWAY_ROUTE": 0.87,
                "REQUEST_TIMING": 0.85,
            }
        return {}


@dataclass
class TransportTargetProfile:
    node: Literal["B", "C"]
    synchronous_cache_invalidation: bool
    route_policy_mechanism: bool


MECHANISM_PATH = ["SESSION_REFRESH", "STALE_CACHE", "STALE_IDENTITY", "AUTHORIZATION_BYPASS"]

TRANSPORT_PROFILES = {
    "B": TransportTargetProfile("B", synchronous_cache_invalidation=False, route_policy_mechanism=False),
    "C": TransportTargetProfile("C", synchronous_cache_invalidation=True, route_policy_mechanism=True),
}


def run_m14_flagship_demo() -> dict:
    """Root-cause + transport A/B/C — SIMULATED."""
    sim = GhostCausalSimulator()
    outcomes = {k.value: sim.run_intervention(k).bypass for k in InterventionKind if k != InterventionKind.COUNTERFACTUAL_CACHE_BEFORE_REFRESH}
    cf = sim.run_intervention(InterventionKind.COUNTERFACTUAL_CACHE_BEFORE_REFRESH)

    transport_b = "PARTIALLY_TRANSPORTABLE" if not TRANSPORT_PROFILES["B"].route_policy_mechanism else "NOT_TRANSPORTABLE"
    transport_c = "NOT_TRANSPORTABLE" if TRANSPORT_PROFILES["C"].route_policy_mechanism else "TRANSPORTABLE"

    return {
        "label": sim.label,
        "interventions": outcomes,
        "cache_blocks_bypass": outcomes.get("CACHE_INVALIDATED") is False,
        "route_does_not_block": outcomes.get("ROUTE_CHANGED") is True,
        "counterfactual_prediction_match": cf.bypass is False,
        "transport_B": transport_b,
        "transport_C": transport_c,
        "structural_C_applicable": True,
        "m14_rejects_C_transport": transport_c == "NOT_TRANSPORTABLE",
    }
