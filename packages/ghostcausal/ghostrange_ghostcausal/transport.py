"""Agents 26–29 — transportability vs M13 structural match."""

from __future__ import annotations

from ghostrange_contracts.ghostcausal_m14 import (
    DomainDifferenceGraphV1,
    TransportabilityQueryV1,
    TransportabilityReportV1,
    TransportabilityStatus,
)

from .simulator import MECHANISM_PATH, TRANSPORT_PROFILES


def analyze_transport(query: TransportabilityQueryV1) -> TransportabilityReportV1:
    target = query.target_domain
    profile = TRANSPORT_PROFILES.get(target)
    if not profile:
        return TransportabilityReportV1(
            query_id=query.query_id,
            status=TransportabilityStatus.INSUFFICIENT_INFORMATION,
            limitations="Unknown target domain",
        )

    if profile.route_policy_mechanism:
        return TransportabilityReportV1(
            query_id=query.query_id,
            status=TransportabilityStatus.NOT_TRANSPORTABLE,
            shared_mechanisms=["SESSION_REFRESH", "PRIVILEGED_DECISION"],
            differing_mechanisms=["CACHE_INVALIDATION_SEMANTICS", "ROUTE_POLICY"],
            required_assumptions=["MECHANISM_INVARIANCE"],
            limitations="Target bypass driven by route policy, not async cache staleness.",
            recommended_local_experiment="do(route_policy_probe)",
        )

    if profile.synchronous_cache_invalidation:
        return TransportabilityReportV1(
            query_id=query.query_id,
            status=TransportabilityStatus.NOT_TRANSPORTABLE,
            differing_mechanisms=["SYNC_CACHE_INVALIDATION"],
            limitations="Structural similarity masks different cache mechanism.",
            recommended_local_experiment="do(cache_invalidation_timing_probe)",
        )

    return TransportabilityReportV1(
        query_id=query.query_id,
        status=TransportabilityStatus.PARTIALLY_TRANSPORTABLE,
        shared_mechanisms=MECHANISM_PATH[:-1],
        required_assumptions=["A3"],
        recommended_local_experiment="do(cache=clean) minimal intervention",
        limitations="Confirm cache semantics locally before claim.",
    )


def domain_difference(source: str, target: str) -> DomainDifferenceGraphV1:
    prof = TRANSPORT_PROFILES.get(target)
    diff = []
    shared = list(MECHANISM_PATH)
    if prof and prof.route_policy_mechanism:
        diff.append("ROUTE_POLICY_MECHANISM")
    if prof and prof.synchronous_cache_invalidation:
        diff.append("CACHE_INVALIDATION_SYNC")
    return DomainDifferenceGraphV1(
        source_domain=source,
        target_domain=target,
        shared_mechanisms=shared,
        differing_mechanisms=diff,
    )


def structural_match_would_transfer(target: str) -> bool:
    """M13 baseline — structural tags overlap."""
    return target in ("B", "C")
