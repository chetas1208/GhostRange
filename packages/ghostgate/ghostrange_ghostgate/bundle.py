"""GhostPromotionBundle export."""

from __future__ import annotations

import hashlib
import json

from ghostrange_contracts.ghostgate_m11 import (
    BundleMode,
    GhostPromotionBundleV1,
    ProductionChangeCandidateV1,
    PromotionAttestationV1,
    ApprovalRequestV1,
    ApprovalDecisionV1,
)

from .canonical import digest_candidate


def build_bundle(
    candidate: ProductionChangeCandidateV1,
    *,
    mode: BundleMode = BundleMode.INTERNAL_FULL,
    approval_request: ApprovalRequestV1 | None = None,
    decisions: list[ApprovalDecisionV1] | None = None,
    experiment_root_digest: str = "",
) -> GhostPromotionBundleV1:
    attestation = None
    if experiment_root_digest and candidate.change_candidate_hash:
        attestation = PromotionAttestationV1(
            experiment_root_digest=experiment_root_digest,
            change_candidate_hash=candidate.change_candidate_hash,
        )
    bundle = GhostPromotionBundleV1(
        mode=mode,
        candidate=candidate,
        approval_request=approval_request,
        approval_decisions=decisions or [],
        attestation=attestation,
    )
    raw = json.dumps(bundle.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    bundle.bundle_digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return bundle


def export_json(bundle: GhostPromotionBundleV1) -> str:
    return json.dumps(bundle.model_dump(mode="json"), indent=2, sort_keys=True)


def refresh_candidate_hash(candidate: ProductionChangeCandidateV1) -> ProductionChangeCandidateV1:
    candidate.change_candidate_hash = digest_candidate(candidate)
    return candidate
