from fastapi.testclient import TestClient

from ghostrange_api.main import create_app


def test_mesh_policy_default_off():
    client = TestClient(create_app())
    r = client.get("/v1/mesh/policy")
    assert r.status_code == 200
    assert r.json()["sharing_enabled"] is False


def test_mesh_demo_story():
    client = TestClient(create_app())
    r = client.post("/v1/mesh/demo/story")
    assert r.status_code == 200
    body = r.json()
    assert body["e_quarantined"] is True
    assert body["b_experiments_first"] == "session_refresh_identity_probe"
