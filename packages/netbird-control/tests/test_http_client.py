"""Tests for the low-level HTTP client: auth header shape, retry/backoff,
and error mapping. All against httpx.MockTransport — no network access, no
real credentials, ever.
"""

from __future__ import annotations

import httpx
import pytest

from ghostrange_netbird_control.errors import (
    NetBirdAuthError,
    NetBirdControlError,
    NetBirdNotFoundError,
    NetBirdRateLimitedError,
    NetBirdServerError,
    NetBirdTimeoutError,
    NetBirdUnavailableError,
    NetBirdValidationError,
)
from ghostrange_netbird_control.http_client import NetBirdHTTPClient

FAKE_TOKEN = "nbtok-test-not-a-real-netbird-token-0000"


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    monkeypatch.setattr("ghostrange_netbird_control.http_client.time.sleep", lambda _s: None)


def client_with(handler, **kwargs) -> NetBirdHTTPClient:
    return NetBirdHTTPClient(api_token=FAKE_TOKEN, transport=httpx.MockTransport(handler), **kwargs)


class TestAuth:
    def test_missing_api_token_raises_before_any_request(self, monkeypatch):
        monkeypatch.delenv("NETBIRD_API_TOKEN", raising=False)
        with pytest.raises(NetBirdAuthError):
            NetBirdHTTPClient()

    def test_env_var_is_used_when_no_explicit_token(self, monkeypatch):
        monkeypatch.setenv("NETBIRD_API_TOKEN", FAKE_TOKEN)
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json=[])

        client = NetBirdHTTPClient(transport=httpx.MockTransport(handler))
        client.request("GET", "/api/peers")
        assert seen["auth"] == f"Token {FAKE_TOKEN}"

    def test_token_auth_header_uses_token_scheme_not_bearer(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json=[])

        client_with(handler).request("GET", "/api/peers")
        assert seen["auth"] == f"Token {FAKE_TOKEN}"
        assert not seen["auth"].startswith("Bearer")

    def test_api_token_never_appears_in_exception_text(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"message": "not found"})

        client = client_with(handler)
        with pytest.raises(NetBirdNotFoundError) as exc_info:
            client.request("GET", "/api/peers/nope")
        assert FAKE_TOKEN not in str(exc_info.value)
        assert FAKE_TOKEN not in repr(exc_info.value)


class TestSuccessResponses:
    def test_200_json_is_parsed(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[{"id": "p1"}])

        result = client_with(handler).request("GET", "/api/peers")
        assert result == [{"id": "p1"}]

    def test_204_returns_none(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(204)

        result = client_with(handler).request("DELETE", "/api/peers/p1")
        assert result is None


class TestErrorMapping:
    @pytest.mark.parametrize(
        "status_code,expected_exc",
        [
            (401, NetBirdAuthError),
            (403, NetBirdAuthError),
            (404, NetBirdNotFoundError),
            (400, NetBirdValidationError),
            (422, NetBirdValidationError),
            (418, NetBirdControlError),
        ],
    )
    def test_status_maps_to_typed_error(self, status_code, expected_exc):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code, json={"message": f"boom {status_code}"})

        with pytest.raises(expected_exc) as exc_info:
            client_with(handler).request("GET", "/api/peers/p1")
        assert exc_info.value.status_code == status_code
        assert f"boom {status_code}" in str(exc_info.value)

    def test_4xx_is_not_retried(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(400, json={"message": "bad request"})

        with pytest.raises(NetBirdValidationError):
            client_with(handler, max_retries=5).request("POST", "/api/setup-keys")
        assert calls["count"] == 1


class TestRetryOn429And5xx:
    def test_429_retries_then_succeeds(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] < 3:
                return httpx.Response(429, json={"message": "rate limited"})
            return httpx.Response(200, json=[])

        result = client_with(handler, max_retries=5).request("GET", "/api/peers")
        assert result == []
        assert calls["count"] == 3

    def test_429_exhausts_retry_budget_and_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"message": "rate limited"})

        with pytest.raises(NetBirdRateLimitedError):
            client_with(handler, max_retries=2).request("GET", "/api/peers")

    def test_5xx_retries_then_raises_server_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"message": "upstream unavailable"})

        with pytest.raises(NetBirdServerError):
            client_with(handler, max_retries=2).request("GET", "/api/peers")

    def test_network_error_retries_then_raises_unavailable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        with pytest.raises(NetBirdUnavailableError):
            client_with(handler, max_retries=1).request("GET", "/api/peers")

    def test_timeout_retries_then_raises_timeout_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timed out")

        with pytest.raises(NetBirdTimeoutError):
            client_with(handler, max_retries=1).request("GET", "/api/peers")
