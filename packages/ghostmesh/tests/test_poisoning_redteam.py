"""Agent 37 — malicious node attacks."""

from ghostrange_ghostmesh.coordinator import MeshCoordinator
from ghostrange_ghostmesh.extract import extract_poisoned_contribution_candidate
from ghostrange_ghostmesh.harness import GhostMeshHarness
from ghostrange_ghostmesh.sybil import ContributionQuotaTracker
from ghostrange_contracts.ghostmesh_m13 import MeshFederationV1


def test_poison_not_published():
    h = GhostMeshHarness()
    e = h.nodes["E"]
    prep = e.prepare_contribution(extract_poisoned_contribution_candidate(local_source_ref="evil"))
    assert not prep.ok


def test_sybil_quota_blocks_spam():
    q = ContributionQuotaTracker(max_per_node_per_day=2)
    assert q.allow("E", "c1")
    assert q.allow("E", "c2")
    assert not q.allow("E", "c3")


def test_non_member_rejected():
    coord = MeshCoordinator(federation=MeshFederationV1(federation_id="f"), members={"A"})
    from ghostrange_ghostmesh.harness import run_m13_demo_story
    from ghostrange_ghostmesh.extract import extract_session_refresh_counterexample
    from ghostrange_ghostmesh.privacy_transform import transform_candidate
    from ghostrange_contracts.ghostmesh_m13 import KnowledgeClass, MeshContributionPolicyV1, MeshDisclosureLevel

    pol = MeshContributionPolicyV1(
        sharing_enabled=True,
        allowed_knowledge_classes=[KnowledgeClass.COUNTEREXAMPLE_PATTERN],
        minimum_local_validations=1,
        minimum_abstraction_tags=2,
        default_disclosure=MeshDisclosureLevel.PSEUDONYMOUS_STRUCTURED,
        require_human_approval=False,
    )
    cand = extract_session_refresh_counterexample(local_source_ref="z", tenant_label="a")
    tr = transform_candidate(cand, policy=pol, contributor_pseudonym="x")
    assert tr.contribution
    ok, reason = coord.accept_contribution("Z", tr.contribution)
    assert not ok and reason == "membership_denied"
