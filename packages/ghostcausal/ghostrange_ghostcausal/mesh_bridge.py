"""Agent 30 — privacy-safe causal mesh contributions."""

from __future__ import annotations

import hashlib
import json

from ghostrange_contracts.ghostcausal_m14 import (
    CausalContributionPrivacyV1,
    CausalMeshContributionV1,
)

from .simulator import MECHANISM_PATH


def abstract_causal_mesh_contribution(*, provenance_ref: str) -> CausalMeshContributionV1:
    digest = hashlib.sha256(json.dumps(MECHANISM_PATH).encode()).hexdigest()
    return CausalMeshContributionV1(
        abstract_variables=["CACHED_IDENTITY", "REFRESH", "PRIVILEGED_DECISION"],
        abstract_mechanism_path=MECHANISM_PATH,
        intervention_class="do(cache=clean)",
        effect_class="AUTHORIZATION_BYPASS",
        assumption_profile=["MECHANISM_INVARIANCE", "TEMPORAL_ORDER"],
        provenance_digest=digest,
    )


def privacy_check(c: CausalMeshContributionV1) -> CausalContributionPrivacyV1:
    risk = "LOW"
    for v in c.abstract_variables:
        if "prod" in v.lower() or "internal" in v.lower():
            risk = "HIGH"
    return CausalContributionPrivacyV1(
        fields_generalized=["service", "hostname", "tenant"],
        topology_leakage_risk=risk,
    )
