"""Privacy transform pipeline — candidate stays local until gate passes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ghostrange_contracts.ghostmesh_m13 import (
    ContributionPrivacyProfileV1,
    KnowledgeClass,
    MeshContributionPolicyV1,
    MeshContributionV1,
    MeshDisclosureLevel,
    MeshCandidateKnowledgeV1,
)

from .abstraction import abstract_from_candidate, default_applicability
from .dlp import scan_contribution_payload, scan_text
from .semantic_privacy import assess_semantic_leakage


@dataclass
class PrivacyTransformResult:
    ok: bool
    contribution: MeshContributionV1 | None = None
    reason: str = ""
    privacy_profile: ContributionPrivacyProfileV1 | None = None


def _digest(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def transform_candidate(
    candidate: MeshCandidateKnowledgeV1,
    *,
    policy: MeshContributionPolicyV1,
    contributor_pseudonym: str,
    local_validation_count: int = 1,
) -> PrivacyTransformResult:
    if not policy.sharing_enabled:
        return PrivacyTransformResult(ok=False, reason="sharing_disabled_default")

    if candidate.knowledge_class not in policy.allowed_knowledge_classes:
        return PrivacyTransformResult(ok=False, reason="knowledge_class_not_allowed")

    if local_validation_count < policy.minimum_local_validations:
        return PrivacyTransformResult(ok=False, reason="insufficient_local_validations")

    # Raw candidate stays local — may contain tenant hostnames; never publish raw.
    smuggle = candidate.raw_internal_summary.get("instruction")
    if smuggle:
        sm = scan_text(str(smuggle))
        if not sm.ok:
            return PrivacyTransformResult(ok=False, reason=f"smuggle_in_candidate:{sm.findings[0].kind}")

    abstract = abstract_from_candidate(candidate)
    if len(abstract.abstract_tags) < policy.minimum_abstraction_tags:
        return PrivacyTransformResult(ok=False, reason="insufficient_abstraction")

    profile = ContributionPrivacyProfileV1(
        fields_removed=["hostname", "raw_url", "tenant_id", "source_code", "raw_logs"],
        fields_generalized=["service", "route", "topology"],
        fields_hashed=["local_evidence_ref"],
        aggregation_required=False,
        minimum_cohort=1,
        residual_leakage_assessment="BENCHMARK_SYNTHETIC",
    )

    payload_preview = {
        "tags": abstract.abstract_tags,
        "class": candidate.knowledge_class.value,
    }
    dlp = scan_contribution_payload(payload_preview)
    if not dlp.ok:
        return PrivacyTransformResult(ok=False, reason=f"dlp_failed:{dlp.findings[0].kind}", privacy_profile=profile)

    provenance_digest = _digest({"source": candidate.local_source_ref, "class": candidate.knowledge_class.value})
    content = {
        "abstract_tags": abstract.abstract_tags,
        "abstract_relations": abstract.abstract_relations,
        "knowledge_class": candidate.knowledge_class.value,
    }
    content_digest = _digest(content)

    contribution = MeshContributionV1(
        knowledge_class=candidate.knowledge_class,
        abstract_pattern=abstract,
        applicability=default_applicability(candidate),
        evidence_strength=0.85,
        local_validation_count=local_validation_count,
        provenance_digest=provenance_digest,
        privacy_profile=profile,
        disclosure_level=MeshDisclosureLevel.PSEUDONYMOUS_STRUCTURED,
        contributor_pseudonym=contributor_pseudonym,
        content_digest=content_digest,
    )

    final_dlp = scan_contribution_payload(contribution.model_dump(mode="json"))
    if not final_dlp.ok:
        return PrivacyTransformResult(ok=False, reason="post_build_dlp_failed", privacy_profile=profile)

    sem = assess_semantic_leakage(contribution)
    if not sem.ok:
        return PrivacyTransformResult(
            ok=False,
            reason=f"semantic_leakage:{sem.risks[0]}",
            privacy_profile=profile,
        )

    return PrivacyTransformResult(ok=True, contribution=contribution, privacy_profile=profile)
