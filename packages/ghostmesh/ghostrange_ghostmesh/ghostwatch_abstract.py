"""Agent 26 — abstract production-surprise patterns (no raw telemetry)."""

from __future__ import annotations

from ghostrange_contracts.ghostmesh_m13 import KnowledgeAbstractionV1, KnowledgeClass, MeshCandidateKnowledgeV1


def abstract_production_surprise(*, local_source_ref: str) -> MeshCandidateKnowledgeV1:
    return MeshCandidateKnowledgeV1(
        knowledge_class=KnowledgeClass.PRODUCTION_SURPRISE_PATTERN,
        local_source_ref=local_source_ref,
        raw_internal_summary={
            "local_service": "auth-v2.7",
            "observation": "latency spike after image update",
            "architecture": "stateful_auth",
        },
    )


def surprise_to_abstraction() -> KnowledgeAbstractionV1:
    return KnowledgeAbstractionV1(
        abstract_tags=["AUTH_SERVICE_UPDATE", "CACHE_INVALIDATION", "LATENCY_REGRESSION_PATTERN"],
        abstract_relations=["DEPLOYMENT", "RUNTIME_INVARIANT"],
        notes="no metric samples included",
    )
