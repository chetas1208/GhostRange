from fastapi.testclient import TestClient

from ghostrange_api.main import create_app


def test_causal_flagship():
    client = TestClient(create_app())
    r = client.post("/v1/causal/demo/flagship")
    assert r.status_code == 200
    assert r.json()["m14_rejects_C_transport"] is True
