from fastapi.testclient import TestClient

from ghostrange_api import investigation_routes
from ghostrange_api.main import create_app
from ghostrange_contracts.derived_system_model import (
    DerivedServiceRole,
    DerivedServiceV1,
    DerivedSystemModelV1,
    DerivationConfidence,
    DerivationProvenanceV1,
    DerivationSourceKind,
    RepoScanSummaryV1,
)
from ghostrange_range_compiler.intake import RepositoryAcquisitionError

VALID_PAYLOAD = {
    "case_id": "auth-incident-031",
    "incident": {
        "title": "Privilege persists after role revocation",
        "description": "A user can still access admin endpoints after their role is revoked.",
        "observed_at": "2026-09-27T07:30:00Z",
    },
    "system": {
        "repository_url": "https://github.com/acme/auth-service",
        "branch": "main",
    },
    "evidence": [],
    "constraints": {"max_workers": 1, "max_cost_usd": 1.0, "live_production_actions": False},
}


def _fake_model() -> DerivedSystemModelV1:
    auth = DerivedServiceV1(
        name="auth",
        inferred_role=DerivedServiceRole.AUTH,
        role_confidence=DerivationConfidence.MEDIUM,
        is_external_interface=True,
        provenance=[
            DerivationProvenanceV1(
                source_kind=DerivationSourceKind.DOCKER_COMPOSE,
                source_path="docker-compose.yml",
                locator="services.auth",
                rule="compose_service_block",
                note="derived from docker-compose.yml service block `auth`",
            )
        ],
    )
    summary = RepoScanSummaryV1(
        files_scanned=47,
        files_relevant=12,
        services_identified=5,
        data_stores_identified=2,
        external_interfaces_identified=1,
    )
    return DerivedSystemModelV1(
        repository_url="https://github.com/acme/auth-service",
        branch="main",
        commit_sha="deadbeef",
        services=[auth],
        summary=summary,
    )


def test_intake_returns_derived_model_and_narration(monkeypatch):
    monkeypatch.setattr(investigation_routes, "analyze_repository", lambda url, branch: _fake_model())
    client = TestClient(create_app())

    resp = client.post("/v1/investigations/intake", json=VALID_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == "auth-incident-031"
    assert body["derived_system_model"]["services"][0]["name"] == "auth"
    assert body["derived_system_model"]["confidence_disclaimer"]
    assert body["narration"] == [
        "Repository acquired.",
        "12 files relevant of 47 scanned.",
        "5 services identified.",
        "2 data stores identified.",
        "1 external interfaces identified.",
    ]


def test_intake_rejects_unsupported_repository(monkeypatch):
    def _raise(url, branch):
        raise RepositoryAcquisitionError(f"Only public https://github.com URLs are supported, got: {url!r}")

    monkeypatch.setattr(investigation_routes, "analyze_repository", _raise)
    client = TestClient(create_app())

    resp = client.post("/v1/investigations/intake", json=VALID_PAYLOAD)

    assert resp.status_code == 422
    assert "github.com" in resp.json()["detail"]


def test_intake_validates_request_shape():
    client = TestClient(create_app())
    resp = client.post(
        "/v1/investigations/intake",
        json={"case_id": "x", "incident": {"title": "t"}},  # missing description, system
    )
    assert resp.status_code == 422


def test_intake_defaults_branch_to_main(monkeypatch):
    captured = {}

    def _fake(url, branch):
        captured["url"] = url
        captured["branch"] = branch
        return _fake_model()

    monkeypatch.setattr(investigation_routes, "analyze_repository", _fake)
    client = TestClient(create_app())

    payload = dict(VALID_PAYLOAD)
    payload["system"] = {"repository_url": "https://github.com/acme/auth-service"}
    resp = client.post("/v1/investigations/intake", json=payload)

    assert resp.status_code == 200
    assert captured["branch"] == "main"
