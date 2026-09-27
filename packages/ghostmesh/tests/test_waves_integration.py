"""Cross-wave integration — federation analytics, model rank, revocation."""

from ghostrange_contracts.ghostmesh_m13 import KnowledgeClass
from ghostrange_ghostmesh.federated_analytics import cohort_validation_rate
from ghostrange_ghostmesh.federated_model import build_model, rank_test_ids
from ghostrange_ghostmesh.harness import GhostMeshHarness
from ghostrange_ghostmesh.registry import MeshKnowledgeRegistry
from ghostrange_ghostmesh.revocation import revoke_contribution
from ghostrange_ghostmesh.search_prior import mesh_priors_to_search_families


def test_revocation_propagation():
    h = GhostMeshHarness()
    demo = h.run_demo_story()
    assert demo.a_published
    a = h.nodes["A"]
    assert h.coordinator
    contrib = next(iter(h.coordinator.registry.contributions.values()))
    revoke_contribution(
        h.coordinator.registry,
        contribution_id=contrib.id,
        revoker_node_id="A",
        reason="operator",
    )
    assert h.coordinator.registry.status(str(contrib.id)).value == "REVOKED"


def test_federated_analytics_min_cohort():
    reg = MeshKnowledgeRegistry()
    assert cohort_validation_rate(reg, KnowledgeClass.COUNTEREXAMPLE_PATTERN, min_cohort=3) is None


def test_search_prior_and_model_rank():
    h = GhostMeshHarness()
    h.run_demo_story()
    b = h.nodes["B"]
    families = mesh_priors_to_search_families(b.local_priors)
    assert families
    ranked = rank_test_ids(b.local_priors, ["broad_auth_scan", "session_refresh_identity_probe"])
    assert ranked[0] == "session_refresh_identity_probe"
    model = build_model(round_id=1, priors=b.local_priors)
    assert model.model_id == "federated-prior-1"
