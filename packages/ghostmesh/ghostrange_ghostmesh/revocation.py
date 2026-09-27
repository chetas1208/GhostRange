"""Agent 20 — revocation propagation."""

from __future__ import annotations

from ghostrange_contracts.ghostmesh_m13 import ContributionRevocationV1, RemoteKnowledgeStatus

from .registry import MeshKnowledgeRegistry


def revoke_contribution(
    registry: MeshKnowledgeRegistry,
    *,
    contribution_id,
    revoker_node_id: str,
    reason: str,
) -> ContributionRevocationV1:
    rev = ContributionRevocationV1(
        contribution_id=contribution_id,
        revoker_node_id=revoker_node_id,
        reason=reason,
    )
    registry.revoke(rev)
    return rev


def remote_status_after_revoke(registry: MeshKnowledgeRegistry, contribution_id: str) -> RemoteKnowledgeStatus:
    return registry.status(contribution_id)
