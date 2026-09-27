from pathlib import Path

from ghostrange_range_compiler import RangeCompiler

FIXTURE = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "compiler" / "compose-basic" / "docker-compose.yml"
AUTH_LAB = (
    Path(__file__).resolve().parents[3]
    / "ranges"
    / "ghostrange-auth-lab-v1"
    / "docker"
    / "vm-1"
    / "docker-compose.yml"
)


def test_compose_basic_graph():
    rc = RangeCompiler()
    result = rc.compile_compose(FIXTURE, range_name="basic")
    assert len(result.graph.nodes) >= 4
    assert result.range_spec.schema_version == "2"
    assert len(result.range_spec.assets) >= 4
    assert result.fidelity_report.valid_for_investigation is False  # plaintext secret in fixture


def test_auth_lab_compose_no_plaintext_secret_rejection():
    rc = RangeCompiler()
    result = rc.compile_compose(AUTH_LAB, range_name="auth-lab-compiled")
    assert result.placement.selected_vm_count == 1
    assert result.errors == []
    assert result.fidelity_report.valid_for_investigation is True


def test_compose_golden_service_names():
    rc = RangeCompiler()
    result = rc.compile_compose(AUTH_LAB)
    names = {a.hostname for a in result.range_spec.assets}
    assert "gateway" in names
    assert "auth" in names
