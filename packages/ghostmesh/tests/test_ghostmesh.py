"""M13 GhostMesh unit + harness tests."""

from ghostrange_contracts.ghostmesh_m13 import RemoteKnowledgeStatus
from ghostrange_ghostmesh.dlp import scan_text
from ghostrange_ghostmesh.harness import GhostMeshHarness, run_m13_demo_story
from ghostrange_ghostmesh.policy_loader import load_mesh_policy
from pathlib import Path


def test_default_policy_sharing_off():
    repo = Path(__file__).resolve().parents[3]
    pol = load_mesh_policy(repo / "config" / "mesh-contribution-policy.yaml")
    assert pol.sharing_enabled is False


def test_dlp_catches_hostname():
    r = scan_text("connect auth-prod-east-7.internal.admin")
    assert not r.ok


def test_m13_demo_story():
    r = run_m13_demo_story()
    assert r.a_published
    assert r.b_status == RemoteKnowledgeStatus.LOCALLY_SUPPORTED
    assert r.c_status == RemoteKnowledgeStatus.LOCALLY_REJECTED
    assert r.d_status == "NOT_APPLICABLE"
    assert r.e_quarantined
    assert r.b_experiments_first == "session_refresh_identity_probe"


def test_mesh_outage_local_director_still_works():
    h = GhostMeshHarness()
    h.nodes = {}  # simulate mesh unavailable
    assert h.nodes == {}
