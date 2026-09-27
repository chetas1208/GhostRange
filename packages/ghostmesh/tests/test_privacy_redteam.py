"""Agent 36 — privacy reconstruction attacks on published contributions."""

from ghostrange_ghostmesh.dlp import scan_text
from ghostrange_ghostmesh.extract import extract_session_refresh_counterexample
from ghostrange_ghostmesh.harness import run_m13_demo_story
from ghostrange_ghostmesh.privacy_transform import transform_candidate
from ghostrange_contracts.ghostmesh_m13 import KnowledgeClass, MeshContributionPolicyV1, MeshDisclosureLevel


def _sharing_policy():
    return MeshContributionPolicyV1(
        sharing_enabled=True,
        allowed_knowledge_classes=[KnowledgeClass.COUNTEREXAMPLE_PATTERN],
        minimum_local_validations=1,
        minimum_abstraction_tags=2,
        default_disclosure=MeshDisclosureLevel.PSEUDONYMOUS_STRUCTURED,
        require_human_approval=False,
        allowed_federation_ids=["bench"],
    )


def test_hostname_not_in_published_contribution():
    cand = extract_session_refresh_counterexample(local_source_ref="x", tenant_label="org-a")
    out = transform_candidate(cand, policy=_sharing_policy(), contributor_pseudonym="p")
    assert out.ok and out.contribution
    blob = out.contribution.model_dump_json()
    assert "auth-prod-east-7" not in blob
    assert "/internal/admin" not in blob


def test_topology_reconstruction_from_tags_fails():
    demo = run_m13_demo_story()
    assert demo.a_published
    # No service count or host graph in harness output
    assert "east-7" not in demo.b_experiments_first


def test_identifier_extraction_attack_strings_blocked():
    assert not scan_text("10.0.0.5 admin@corp.com").ok
