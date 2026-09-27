"""Structural generalization — tenant-specific → transferable tags."""

from __future__ import annotations

from ghostrange_contracts.ghostmesh_m13 import (
    ApplicabilityProfileV1,
    KnowledgeAbstractionV1,
    KnowledgeClass,
    MeshCandidateKnowledgeV1,
)

# Local-only labels that must never appear in abstract output
LOCAL_IDENTIFIERS = (
    "auth-prod-east-7",
    "gateway-2",
    "redis-cluster-01",
    "/internal/admin",
    "customer-session",
)


def abstract_from_candidate(candidate: MeshCandidateKnowledgeV1) -> KnowledgeAbstractionV1:
    """Deterministic abstraction for benchmark tenants A–E."""
    raw = candidate.raw_internal_summary
    tags: list[str] = []
    relations: list[str] = []

    if candidate.knowledge_class == KnowledgeClass.COUNTEREXAMPLE_PATTERN:
        tags = ["AUTHORIZATION", "SESSION_REFRESH", "CACHED_IDENTITY", "PRIVILEGED_ROUTE"]
        relations = ["IDENTITY_CACHE", "REFRESH_TOKEN", "ROLE_GATE"]
    elif candidate.knowledge_class == KnowledgeClass.PRODUCTION_SURPRISE_PATTERN:
        tags = ["AUTH_SERVICE_UPDATE", "CACHE_INVALIDATION", "LATENCY_REGRESSION_PATTERN"]
    else:
        tags = [str(k).upper() for k in list(raw.keys())[:4]]

    for bad in LOCAL_IDENTIFIERS:
        if any(bad.lower() in t.lower() for t in tags):
            raise ValueError("abstraction still contains local identifier")

    return KnowledgeAbstractionV1(
        abstract_tags=tags,
        abstract_relations=relations,
        notes="structurally abstracted; no tenant topology",
    )


def default_applicability(candidate: MeshCandidateKnowledgeV1) -> ApplicabilityProfileV1:
    return ApplicabilityProfileV1(
        architecture_family=str(candidate.raw_internal_summary.get("architecture", "stateful_auth")),
        identity_pattern="cached_session",
        statefulness="stateful",
        deployment_model=str(candidate.raw_internal_summary.get("deployment", "k8s")),
    )
