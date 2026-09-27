from pathlib import Path

from ghostrange_contracts.derived_system_model import DerivedServiceRole
from ghostrange_range_compiler.intake.repo_scanner import scan_directory

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "repo_scan"


def _service(model, name):
    for svc in model.services:
        if svc.name == name:
            return svc
    raise AssertionError(f"service {name!r} not found among {[s.name for s in model.services]}")


def test_compose_repo_identifies_services_and_roles():
    model = scan_directory(FIXTURES / "compose_repo", repository_url="https://github.com/acme/auth-service", branch="main")

    names = {s.name for s in model.services}
    assert names == {"gateway", "auth", "db"}

    gateway = _service(model, "gateway")
    assert gateway.inferred_role == DerivedServiceRole.GATEWAY
    assert gateway.is_external_interface is True
    assert 80 in gateway.ports

    db = _service(model, "db")
    assert db.inferred_role == DerivedServiceRole.DATABASE
    assert db.is_external_interface is True

    auth = _service(model, "auth")
    assert auth.inferred_role == DerivedServiceRole.AUTH
    # picked up from Dockerfile EXPOSE + package.json language, both attached
    # to the same service via its compose build_context.
    assert 8080 in auth.ports
    assert auth.language == "javascript/typescript"
    assert auth.is_external_interface is True  # from EXPOSE + OpenAPI spec


def test_compose_repo_provenance_is_populated_and_auditable():
    model = scan_directory(FIXTURES / "compose_repo", repository_url="x", branch="main")
    for svc in model.services:
        assert svc.provenance, f"service {svc.name} has no provenance — every derived fact must be auditable"
        for prov in svc.provenance:
            assert prov.source_path
            assert prov.note

    auth = _service(model, "auth")
    notes = [p.note for p in auth.provenance]
    assert any("docker-compose.yml" in n and "auth" in n for n in notes)
    assert any("Dockerfile" in n for n in notes)
    assert any("openapi.yaml" in n for n in notes)
    assert any("package.json" in n for n in notes)


def test_compose_depends_on_produces_edges():
    model = scan_directory(FIXTURES / "compose_repo")
    edges = {(e.from_service, e.to_service, e.relationship) for e in model.dependency_edges}
    assert ("gateway", "auth", "depends_on") in edges
    assert ("auth", "db", "depends_on") in edges


def test_env_template_reference_produces_edge():
    model = scan_directory(FIXTURES / "compose_repo")
    env_edges = [e for e in model.dependency_edges if e.relationship == "env_reference"]
    assert any(e.from_service == "gateway" and e.to_service == "auth" for e in env_edges)
    for e in env_edges:
        assert e.provenance and ".env.example" in e.provenance[0].source_path


def test_narration_summary_counts():
    model = scan_directory(FIXTURES / "compose_repo")
    s = model.summary
    assert s.services_identified == 3
    assert s.data_stores_identified == 1  # only db
    assert s.external_interfaces_identified == 3  # gateway, db, auth all publish/expose
    assert s.files_relevant >= 5  # compose + dockerfile + package.json + openapi + env
    assert s.files_scanned >= s.files_relevant
    narration = s.narration()
    assert "3 services identified" in narration
    assert "1 data stores identified" in narration


def test_confidence_disclaimer_present_and_honest():
    model = scan_directory(FIXTURES / "compose_repo")
    assert "heuristic" in model.confidence_disclaimer.lower()
    assert "not verified" in model.confidence_disclaimer.lower()


def test_k8s_manifest_deployment_and_service():
    model = scan_directory(FIXTURES / "k8s_repo")
    assert len(model.services) == 1  # Deployment and Service share the same metadata.name
    svc = model.services[0]
    assert svc.name == "worker-api"
    assert svc.image == "acme/worker-api:1.2.3"
    assert 9090 in svc.ports
    assert 443 in svc.ports
    assert svc.is_external_interface is True  # LoadBalancer type
    kinds = {p.rule for p in svc.provenance}
    assert "k8s_manifest_kind" in kinds


def test_terraform_resource_blocks_identified():
    model = scan_directory(FIXTURES / "terraform_repo")
    names = {s.name for s in model.services}
    assert names == {"primary", "app_lb"}
    db = _service(model, "primary")
    assert db.inferred_role == DerivedServiceRole.DATABASE
    lb = _service(model, "app_lb")
    assert lb.is_external_interface is True


def test_ignored_directories_are_not_walked():
    model = scan_directory(FIXTURES / "ignored_dirs_repo")
    # node_modules/junk/should_not_count.js must never be counted or read.
    assert model.summary.files_scanned == 1
    assert model.summary.services_identified == 1


def test_scan_is_best_effort_not_high_confidence():
    """No individual role guess should ever claim more than 'medium' confidence —
    this is heuristic file/pattern matching, not verified static analysis."""
    model = scan_directory(FIXTURES / "compose_repo")
    for svc in model.services:
        assert svc.role_confidence.value in ("low", "medium")
