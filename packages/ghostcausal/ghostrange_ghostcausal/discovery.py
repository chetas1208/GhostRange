"""Agents 09–11 — pluggable discovery backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ghostrange_contracts.ghostcausal_m14 import (
    CausalDiscoveryMethodProfileV1,
    CausalEdgeKind,
    CausalEdgeOrigin,
    CausalEdgeStatus,
    CausalEdgeV1,
    CausalAssumptionKind,
)


class CausalDiscoveryBackendV1(ABC):
    @abstractmethod
    def profile(self) -> CausalDiscoveryMethodProfileV1: ...

    @abstractmethod
    def propose_edges(self, correlations: dict[str, float], outcome: str) -> list[CausalEdgeV1]: ...


class CorrelationHeuristicBackend(CausalDiscoveryBackendV1):
    def profile(self) -> CausalDiscoveryMethodProfileV1:
        return CausalDiscoveryMethodProfileV1(
            method="CORRELATION_HEURISTIC",
            assumptions=[CausalAssumptionKind.CAUSAL_SUFFICIENCY],
            failure_modes=["confounding", "spurious_correlation"],
        )

    def propose_edges(self, correlations: dict[str, float], outcome: str) -> list[CausalEdgeV1]:
        edges: list[CausalEdgeV1] = []
        for var, r in correlations.items():
            if r > 0.8:
                edges.append(
                    CausalEdgeV1(
                        source_id=var,
                        target_id=outcome,
                        kind=CausalEdgeKind.POSSIBLY_CAUSES,
                        status=CausalEdgeStatus.OBSERVATION_SUPPORTED,
                        origin=CausalEdgeOrigin.OBSERVATION_INFERRED,
                    )
                )
        return edges


class TemporalConstraintBackend(CausalDiscoveryBackendV1):
    def profile(self) -> CausalDiscoveryMethodProfileV1:
        return CausalDiscoveryMethodProfileV1(
            method="TEMPORAL_CONSTRAINT",
            supports_temporal_data=True,
            assumptions=[CausalAssumptionKind.TEMPORAL_ORDER],
            failure_modes=["timing_not_causation"],
        )

    def propose_edges(self, correlations: dict[str, float], outcome: str) -> list[CausalEdgeV1]:
        order = ["SESSION_REFRESH", "STALE_CACHE", "STALE_IDENTITY", outcome]
        edges: list[CausalEdgeV1] = []
        for i in range(len(order) - 1):
            edges.append(
                CausalEdgeV1(
                    source_id=order[i],
                    target_id=order[i + 1],
                    kind=CausalEdgeKind.POSSIBLY_CAUSES,
                    status=CausalEdgeStatus.HYPOTHESIZED,
                    origin=CausalEdgeOrigin.OBSERVATION_INFERRED,
                )
            )
        return edges
