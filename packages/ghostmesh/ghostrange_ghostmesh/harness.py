"""Five-node GhostMeshHarness — hard tenant isolation; Mesh protocol only cross-boundary."""

from __future__ import annotations

from dataclasses import dataclass, field

from ghostrange_contracts.ghostmesh_m13 import (
    KnowledgeClass,
    LocalNormalizedGraphV1,
    MeshContributionPolicyV1,
    MeshDisclosureLevel,
    MeshFederationV1,
    MeshNodeIdentityV1,
    RemoteKnowledgeStatus,
)

from .extract import extract_poisoned_contribution_candidate, extract_session_refresh_counterexample
from .coordinator import MeshCoordinator
from .mesh import GhostMeshNode


def _policy_sharing_on() -> MeshContributionPolicyV1:
    return MeshContributionPolicyV1(
        sharing_enabled=True,
        allowed_knowledge_classes=[KnowledgeClass.COUNTEREXAMPLE_PATTERN],
        minimum_local_validations=1,
        minimum_abstraction_tags=2,
        default_disclosure=MeshDisclosureLevel.PSEUDONYMOUS_STRUCTURED,
        require_human_approval=False,
        allowed_federation_ids=["bench-consortium"],
    )


def _node(node_id: str, pseudonym: str, tags: list[str]) -> GhostMeshNode:
    return GhostMeshNode(
        identity=MeshNodeIdentityV1(
            node_id=node_id,
            public_key_fingerprint=f"pk-{node_id}",
            federation_ids=["bench-consortium"],
            display_pseudonym=pseudonym,
        ),
        policy=_policy_sharing_on(),
        local_graph=LocalNormalizedGraphV1(tags=tags, capability_flags={"stateful_auth": True}),
    )


@dataclass
class M13DemoResult:
    a_published: bool
    b_status: RemoteKnowledgeStatus
    c_status: RemoteKnowledgeStatus
    d_status: str
    e_quarantined: bool
    b_experiments_first: str
    label: str = "SIMULATED_MESH_HARNESS"


@dataclass
class GhostMeshHarness:
    federation: MeshFederationV1 = field(
        default_factory=lambda: MeshFederationV1(
            federation_id="bench-consortium",
            minimum_cohort_release=3,
            accepted_disclosure_levels=[MeshDisclosureLevel.PSEUDONYMOUS_STRUCTURED],
        )
    )
    coordinator: MeshCoordinator | None = None
    nodes: dict[str, GhostMeshNode] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.nodes:
            self.coordinator = MeshCoordinator(federation=self.federation)
            self.nodes = {
                "A": _node("A", "member-alpha", []),
                "B": _node(
                    "B",
                    "member-beta",
                    ["SESSION_REFRESH", "CACHED_IDENTITY", "PRIVILEGED_ROUTE", "AUTHORIZATION"],
                ),
                "C": _node(
                    "C",
                    "member-gamma",
                    ["SESSION_REFRESH", "SUPERFICIAL_AUTH", "DECOY_MECHANISM"],
                ),
                "D": _node("D", "member-delta", ["UNRELATED_ARCH"]),
                "E": _node("E", "member-epsilon", []),
            }

    def coordinator_publish(self, from_node: str, contribution) -> bool:
        """Coordinator sees digests only — not raw evidence."""
        if not self.nodes[from_node].publish(contribution):
            return False
        if self.coordinator:
            ok, _reason = self.coordinator.accept_contribution(from_node, contribution)
            return ok
        return True

    def deliver_to_all(self, contribution) -> None:
        for nid, node in self.nodes.items():
            if nid == "A":
                continue
            node.receive(contribution)

    def run_demo_story(self) -> M13DemoResult:
        a = self.nodes["A"]
        prep = a.prepare_contribution(
            extract_session_refresh_counterexample(local_source_ref="ledger:A:exp-1", tenant_label="org-a")
        )
        if not prep.ok or not prep.contribution:
            return M13DemoResult(False, RemoteKnowledgeStatus.UNSEEN, RemoteKnowledgeStatus.UNSEEN, "skip", False, "")

        published = self.coordinator_publish("A", prep.contribution)
        if published:
            self.deliver_to_all(prep.contribution)

        cid = str(prep.contribution.id)
        b = self.nodes["B"]
        c = self.nodes["C"]
        d = self.nodes["D"]

        b_rep = b.evaluate(cid)
        b_val = b.validate_local(cid, confirmed=True) if b_rep else RemoteKnowledgeStatus.UNSEEN
        ex = b.director_experiments(cid)
        first = ex[0].test_id if ex else ""

        c_rep = c.evaluate(cid)
        c_val = c.validate_local(cid, confirmed=False) if c_rep else RemoteKnowledgeStatus.UNSEEN

        d_rep = d.evaluate(cid)
        d_status = d_rep.result.value if d_rep else "UNSEEN"

        e = self.nodes["E"]
        poison_prep = e.prepare_contribution(
            extract_poisoned_contribution_candidate(local_source_ref="ledger:E:evil")
        )
        e_quarantine = not poison_prep.ok
        if poison_prep.ok and poison_prep.contribution:
            e_quarantine = not e.publish(poison_prep.contribution) or e.registry.status(
                str(poison_prep.contribution.id)
            ) == RemoteKnowledgeStatus.QUARANTINED

        return M13DemoResult(
            a_published=published,
            b_status=b_val,
            c_status=c_val,
            d_status=d_status,
            e_quarantined=e_quarantine,
            b_experiments_first=first,
        )


def run_m13_demo_story() -> M13DemoResult:
    return GhostMeshHarness().run_demo_story()
