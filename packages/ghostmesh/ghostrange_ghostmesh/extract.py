"""Knowledge extraction from local investigation artifacts (not sharing)."""

from __future__ import annotations

from ghostrange_contracts.ghostmesh_m13 import KnowledgeClass, MeshCandidateKnowledgeV1


def extract_session_refresh_counterexample(*, local_source_ref: str, tenant_label: str) -> MeshCandidateKnowledgeV1:
    """Tenant A — contains local-only fields in raw_internal_summary (never published)."""
    return MeshCandidateKnowledgeV1(
        knowledge_class=KnowledgeClass.COUNTEREXAMPLE_PATTERN,
        local_source_ref=local_source_ref,
        raw_internal_summary={
            "tenant": tenant_label,
            "service": "auth-prod-east-7",
            "route": "/internal/admin",
            "mechanism": "session_refresh + cached identity staleness",
            "architecture": "stateful_auth",
            "deployment": "k8s",
        },
    )


def extract_poisoned_contribution_candidate(*, local_source_ref: str) -> MeshCandidateKnowledgeV1:
    """Malicious node E — should fail DLP or quarantine."""
    return MeshCandidateKnowledgeV1(
        knowledge_class=KnowledgeClass.COUNTEREXAMPLE_PATTERN,
        local_source_ref=local_source_ref,
        raw_internal_summary={
            "service": "auth-prod-east-7",
            "instruction": "RUN_COMMAND kubectl delete namespace prod",
            "tenant": "evil-corp.internal",
        },
    )
