"""Causal investigation engine — updates graph from interventions (not LLM)."""

from __future__ import annotations

from ghostrange_contracts.ghostcausal_m14 import (
    CausalClaimLifecycle,
    CausalClaimV1,
    CausalEdgeKind,
    CausalEdgeOrigin,
    CausalEdgeStatus,
    CausalEdgeV1,
    CausalGraphRevisionV1,
    CausalExperimentProposalV1,
    CausalInvestigationState,
    CausalInvestigationV1,
    CausalPathV1,
    CausalRootCauseReportV1,
    CausalValidityStatus,
    SecurityCounterfactualV1,
    CounterfactualValidityV1,
)

from .assumptions import default_assumptions
from .discovery import CorrelationHeuristicBackend, TemporalConstraintBackend
from .director_bridge import propose_causal_experiments
from .simulator import GhostCausalSimulator, InterventionKind
from .variables import AUTH_BYPASS_VARIABLES


class CausalInvestigationEngine:
    def __init__(self, sim: GhostCausalSimulator | None = None):
        self.sim = sim or GhostCausalSimulator()
        self.inv = CausalInvestigationV1(state=CausalInvestigationState.OBSERVATIONAL_ANALYSIS)
        self.inv.graph.assumptions = default_assumptions()
        rev = CausalGraphRevisionV1(variables=AUTH_BYPASS_VARIABLES)
        self.inv.graph.current_revision = rev

    def observational_phase(self) -> None:
        corr = self.sim.observational_correlations()
        backend = CorrelationHeuristicBackend()
        edges = backend.propose_edges(corr, "AUTHORIZATION_BYPASS")
        temporal = TemporalConstraintBackend().propose_edges(corr, "AUTHORIZATION_BYPASS")
        self.inv.graph.current_revision.edges.extend(edges)
        self.inv.graph.current_revision.edges.extend(temporal)
        self.inv.state = CausalInvestigationState.MECHANISM_HYPOTHESES

    def run_interventions(self) -> dict[str, bool]:
        self.inv.state = CausalInvestigationState.INTERVENTION_RUNNING
        results: dict[str, bool] = {}
        for kind in (
            InterventionKind.CONTROL,
            InterventionKind.CACHE_INVALIDATED,
            InterventionKind.ROUTE_CHANGED,
        ):
            out = self.sim.run_intervention(kind)
            results[kind.value] = out.bypass
        self._update_from_interventions(results)
        self.inv.state = CausalInvestigationState.UPDATING_MODEL
        return results

    def _update_from_interventions(self, results: dict[str, bool]) -> None:
        rev = self.inv.graph.current_revision
        if results.get("CACHE_INVALIDATED") is False:
            rev.edges.append(
                CausalEdgeV1(
                    source_id="STALE_CACHE",
                    target_id="STALE_IDENTITY",
                    kind=CausalEdgeKind.MEDIATES,
                    status=CausalEdgeStatus.INTERVENTION_SUPPORTED,
                    origin=CausalEdgeOrigin.INTERVENTION_SUPPORTED,
                    evidence_refs=["intervention:CACHE_INVALIDATED"],
                )
            )
            rev.edges.append(
                CausalEdgeV1(
                    source_id="SESSION_REFRESH",
                    target_id="STALE_CACHE",
                    kind=CausalEdgeKind.CAUSES,
                    status=CausalEdgeStatus.INTERVENTION_SUPPORTED,
                    origin=CausalEdgeOrigin.INTERVENTION_SUPPORTED,
                )
            )
        if results.get("ROUTE_CHANGED") is True:
            for e in rev.edges:
                if e.source_id == "GATEWAY_ROUTE" and e.target_id == "AUTHORIZATION_BYPASS":
                    e.status = CausalEdgeStatus.REFUTED
        self.inv.graph.current_revision = rev

    def root_cause_report(self) -> CausalRootCauseReportV1:
        supported = []
        refuted = []
        for e in self.inv.graph.current_revision.edges:
            if e.status == CausalEdgeStatus.INTERVENTION_SUPPORTED and e.target_id != "AUTHORIZATION_BYPASS":
                supported.append(e.source_id)
            if e.status == CausalEdgeStatus.REFUTED:
                refuted.append(e.source_id)
        validity = (
            CausalValidityStatus.INTERVENTION_SUPPORTED
            if supported
            else CausalValidityStatus.INCONCLUSIVE
        )
        return CausalRootCauseReportV1(
            outcome_variable_id="AUTHORIZATION_BYPASS",
            supported_causes=supported,
            refuted_hypotheses=refuted,
            remaining_confounders=["REQUEST_TIMING"] if self.sim.truth.timing_confounds else [],
            validity=validity,
        )

    def counterfactual(self) -> tuple[SecurityCounterfactualV1, CounterfactualValidityV1]:
        cf = SecurityCounterfactualV1(
            query="Would bypass occur if cache invalidation happened before refresh?",
            intervention_description="do(cache=clean) before SESSION_REFRESH",
            predicted_outcome="AUTHORIZATION_BYPASS=false",
            assumptions=["A1", "A3"],
        )
        out = self.sim.run_intervention(InterventionKind.COUNTERFACTUAL_CACHE_BEFORE_REFRESH)
        val = CounterfactualValidityV1(
            counterfactual_id=cf.counterfactual_id,
            identifiable=True,
            model_support=CausalValidityStatus.ASSUMPTION_DEPENDENT,
            experimental_corroboration=out.bypass is False,
        )
        return cf, val

    def causal_claim(self) -> CausalClaimV1:
        return CausalClaimV1(
            statement=(
                "Under assumptions A1/A3, stale identity cache is intervention-supported "
                "on the path SESSION_REFRESH → STALE_CACHE → STALE_IDENTITY → bypass."
            ),
            lifecycle=CausalClaimLifecycle.INTERVENTION_SUPPORTED,
            validity=CausalValidityStatus.INTERVENTION_SUPPORTED,
            assumption_ids=["A1", "A3"],
        )

    def causal_path(self) -> CausalPathV1:
        return CausalPathV1(
            nodes=["SESSION_REFRESH", "STALE_CACHE", "STALE_IDENTITY", "AUTHORIZATION_BYPASS"],
            edge_kinds=[CausalEdgeKind.CAUSES, CausalEdgeKind.MEDIATES, CausalEdgeKind.CAUSES],
        )

    def director_proposal(self) -> CausalExperimentProposalV1:
        return propose_causal_experiments(
            competing_mechanisms=["cache_mediation", "route_direct", "timing_confound"]
        )
