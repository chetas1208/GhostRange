"""Single GhostMesh node — local ledger isolation."""

from __future__ import annotations

from dataclasses import dataclass, field

from ghostrange_contracts.ghostmesh_m13 import (
    ApplicabilityReportV1,
    KnowledgeClass,
    LocalNormalizedGraphV1,
    MeshCandidateKnowledgeV1,
    MeshContributionPolicyV1,
    MeshContributionV1,
    MeshNodeIdentityV1,
    MeshPriorV1,
    MeshReceiptV1,
    RemoteKnowledgeStatus,
)

from .applicability import check_applicability
from .director_bridge import PrioritizedExperiment, prioritize_with_mesh_priors
from .poisoning import should_quarantine
from .privacy_transform import PrivacyTransformResult, transform_candidate
from .protocol import wrap_message
from ghostrange_contracts.ghostmesh_m13 import MeshProtocolMessageKind
from .ledger_bridge import MeshProvenanceLog
from .registry import MeshKnowledgeRegistry
from .semantic_privacy import assess_semantic_leakage


@dataclass
class GhostMeshNode:
    identity: MeshNodeIdentityV1
    policy: MeshContributionPolicyV1
    local_graph: LocalNormalizedGraphV1
    registry: MeshKnowledgeRegistry = field(default_factory=MeshKnowledgeRegistry)
    receipts: list[MeshReceiptV1] = field(default_factory=list)
    local_priors: list[MeshPriorV1] = field(default_factory=list)
    remote_status: dict[str, RemoteKnowledgeStatus] = field(default_factory=dict)
    provenance: MeshProvenanceLog = field(default_factory=MeshProvenanceLog)

    def prepare_contribution(self, candidate: MeshCandidateKnowledgeV1) -> PrivacyTransformResult:
        self.provenance.record("mesh.contribution_extracted", candidate.local_source_ref)
        return transform_candidate(
            candidate,
            policy=self.policy,
            contributor_pseudonym=self.identity.display_pseudonym,
            local_validation_count=max(1, candidate.raw_internal_summary.get("local_validations", 1)),
        )

    def publish(self, contribution: MeshContributionV1) -> bool:
        self.provenance.record(
            "mesh.contribution_privacy_checked",
            contribution.content_digest,
            profile=contribution.privacy_profile.model_dump(mode="json"),
        )
        sem = assess_semantic_leakage(contribution)
        if not sem.ok:
            self.provenance.record("mesh.contribution_rejected", contribution.content_digest, reason=sem.risks)
            return False
        if should_quarantine(contribution):
            self.registry.quarantine(str(contribution.id), reason="poisoning_signal")
            self.remote_status[str(contribution.id)] = RemoteKnowledgeStatus.QUARANTINED
            return False
        envelope = wrap_message(
            federation_id=self.identity.federation_ids[0] if self.identity.federation_ids else "local",
            sender_node_id=self.identity.node_id,
            message_kind=MeshProtocolMessageKind.CONTRIBUTION,
            payload=contribution.model_dump(mode="json"),
        )
        _ = envelope
        self.registry.upsert(contribution)
        self.provenance.record("mesh.contribution_published", contribution.content_digest)
        return True

    def receive(self, contribution: MeshContributionV1) -> MeshReceiptV1:
        if should_quarantine(contribution):
            self.registry.quarantine(str(contribution.id))
            status = RemoteKnowledgeStatus.QUARANTINED
        else:
            self.registry.upsert(contribution)
            status = RemoteKnowledgeStatus.ELIGIBLE
        self.remote_status[str(contribution.id)] = status
        receipt = MeshReceiptV1(
            contribution_digest=contribution.content_digest,
            verifying_node_id=self.identity.node_id,
            policy_digest="mesh-policy-v1",
            local_decision=status,
        )
        self.receipts.append(receipt)
        self.provenance.record("mesh.contribution_received", contribution.content_digest, status=status.value)
        if status == RemoteKnowledgeStatus.ELIGIBLE:
            self.local_priors.append(
                MeshPriorV1(
                    source_contribution_id=contribution.id,
                    knowledge_class=contribution.knowledge_class,
                    abstract_tags=list(contribution.abstract_pattern.abstract_tags),
                    applicability_hint="federated_prior",
                    exploration_weight=0.25,
                )
            )
        return receipt

    def evaluate(self, contribution_id: str) -> ApplicabilityReportV1 | None:
        c = self.registry.contributions.get(contribution_id)
        if not c:
            return None
        return check_applicability(c, self.local_graph)

    def validate_local(
        self,
        contribution_id: str,
        *,
        confirmed: bool,
    ) -> RemoteKnowledgeStatus:
        rep = self.evaluate(contribution_id)
        if not rep:
            return RemoteKnowledgeStatus.UNSEEN
        if rep.result.value == "NOT_APPLICABLE":
            st = RemoteKnowledgeStatus.LOCALLY_REJECTED
        elif confirmed:
            st = RemoteKnowledgeStatus.LOCALLY_SUPPORTED
        else:
            st = RemoteKnowledgeStatus.LOCALLY_REJECTED
        self.remote_status[contribution_id] = st
        ev = "mesh.local_validation_passed" if st == RemoteKnowledgeStatus.LOCALLY_SUPPORTED else "mesh.local_validation_failed"
        self.provenance.record(ev, contribution_id, status=st.value)
        return st

    def director_experiments(self, contribution_id: str) -> list[PrioritizedExperiment]:
        base = [
            PrioritizedExperiment("broad_auth_scan", "Broad authorization scan", 0.0, "LOCAL_ONLY"),
            PrioritizedExperiment("gateway_route_probe", "Gateway routing probe", 0.0, "LOCAL_ONLY"),
        ]
        rep = self.evaluate(contribution_id)
        if not rep:
            return base
        return prioritize_with_mesh_priors(base, self.local_priors, rep.result)
