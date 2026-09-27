"""Tests for the low-level HTTP client: auth, retry/backoff, rate-limit
awareness, and error mapping. All against httpx.MockTransport — no network
access, no real credentials, ever.
"""

from __future__ import annotations

import httpx
import pytest

from ghostrange_vultr_control.errors import (
    VultrAuthError,
    VultrConflictError,
    VultrControlError,
    VultrNotFoundError,
    VultrRateLimitedError,
    VultrServerError,
    VultrTimeoutError,
    VultrUnavailableError,
    VultrValidationError,
)
from ghostrange_vultr_control.http_client import VultrHTTPClient, _RateLimiter


FAKE_KEY = "sk-test-not-a-real-vultr-key-0000000000"


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    """Every backoff test uses tiny/zero delays already, but patch out
    time.sleep entirely so a bug that computes a large delay can't hang the
    suite."""
    monkeypatch.setattr("ghostrange_vultr_control.http_client.time.sleep", lambda _s: None)


def client_with(handler, **kwargs) -> VultrHTTPClient:
    return VultrHTTPClient(
        api_key=FAKE_KEY,
        transport=httpx.MockTransport(handler),
        requests_per_second=10_000,  # don't let the self-throttle slow tests down
        **kwargs,
    )


class TestAuth:
    def test_missing_api_key_raises_before_any_request(self, monkeypatch):
        monkeypatch.delenv("VULTR_API_KEY", raising=False)
        with pytest.raises(VultrAuthError):
            VultrHTTPClient()

    def test_env_var_is_used_when_no_explicit_key(self, monkeypatch):
        monkeypatch.setenv("VULTR_API_KEY", FAKE_KEY)
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json={"ok": True})

        client = VultrHTTPClient(transport=httpx.MockTransport(handler))
        client.request("GET", "/v2/instances")
        assert seen["auth"] == f"Bearer {FAKE_KEY}"

    def test_bearer_header_sent(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json={"ok": True})

        client_with(handler).request("GET", "/v2/instances")
        assert seen["auth"] == f"Bearer {FAKE_KEY}"

    def test_api_key_never_appears_in_exception_text(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "not found"})

        client = client_with(handler)
        with pytest.raises(VultrNotFoundError) as exc_info:
            client.request("GET", "/v2/instances/nope")
        assert FAKE_KEY not in str(exc_info.value)
        assert FAKE_KEY not in repr(exc_info.value)


class TestSuccessResponses:
    def test_200_json_is_parsed(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"instance": {"id": "abc"}})

        result = client_with(handler).request("GET", "/v2/instances/abc")
        assert result == {"instance": {"id": "abc"}}

    def test_204_returns_none(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(204)

        result = client_with(handler).request("DELETE", "/v2/instances/abc")
        assert result is None

    def test_202_accepted_is_parsed(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(202, json={"vpc": {"id": "vpc-1"}})

        result = client_with(handler).request("POST", "/v2/vpcs")
        assert result == {"vpc": {"id": "vpc-1"}}


class TestErrorMapping:
    @pytest.mark.parametrize(
        "status_code,expected_exc",
        [
            (401, VultrAuthError),
            (403, VultrAuthError),
            (404, VultrNotFoundError),
            (409, VultrConflictError),
            (400, VultrValidationError),
            (422, VultrValidationError),
            (418, VultrControlError),  # anything unrecognized still becomes *a* typed error
        ],
    )
    def test_status_maps_to_typed_error(self, status_code, expected_exc):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code, json={"error": f"boom {status_code}"})

        with pytest.raises(expected_exc) as exc_info:
            client_with(handler).request("GET", "/v2/instances/abc")
        assert exc_info.value.status_code == status_code
        assert f"boom {status_code}" in str(exc_info.value)

    def test_4xx_is_not_retried(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(400, json={"error": "bad request"})

        with pytest.raises(VultrValidationError):
            client_with(handler, max_retries=5).request("POST", "/v2/instances")
        assert calls["count"] == 1

    def test_error_message_without_json_body_falls_back_to_default(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, content=b"not json")

        with pytest.raises(VultrNotFoundError) as exc_info:
            client_with(handler).request("GET", "/v2/instances/abc")
        assert "404" in str(exc_info.value)


class TestRetryOn429:
    def test_retries_then_succeeds(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] < 3:
                return httpx.Response(429, json={"error": "rate limited"})
            return httpx.Response(200, json={"ok": True})

        result = client_with(handler, max_retries=5).request("GET", "/v2/instances")
        assert result == {"ok": True}
        assert calls["count"] == 3

    def test_exhausts_retry_budget_and_raises(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(429, json={"error": "rate limited"})

        with pytest.raises(VultrRateLimitedError):
            client_with(handler, max_retries=2).request("GET", "/v2/instances")
        assert calls["count"] == 3  # initial attempt + 2 retries

    def test_retry_after_header_is_honored(self, monkeypatch):
        sleeps = []
        monkeypatch.setattr("ghostrange_vultr_control.http_client.time.sleep", lambda s: sleeps.append(s))

        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] == 1:
                return httpx.Response(429, headers={"Retry-After": "7"}, json={"error": "rate limited"})
            return httpx.Response(200, json={"ok": True})

        client_with(handler, max_retries=3).request("GET", "/v2/instances")
        assert sleeps[0] == 7.0


class TestRetryOn5xxAndNetworkErrors:
    def test_5xx_retries_then_raises_server_error(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(503, json={"error": "upstream unavailable"})

        with pytest.raises(VultrServerError):
            client_with(handler, max_retries=2).request("GET", "/v2/instances")
        assert calls["count"] == 3

    def test_5xx_retries_then_succeeds(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] < 2:
                return httpx.Response(500, json={"error": "internal error"})
            return httpx.Response(200, json={"ok": True})

        result = client_with(handler, max_retries=3).request("GET", "/v2/instances")
        assert result == {"ok": True}

    def test_network_error_retries_then_raises_unavailable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        with pytest.raises(VultrUnavailableError):
            client_with(handler, max_retries=2).request("GET", "/v2/instances")

    def test_timeout_retries_then_raises_timeout_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timed out")

        with pytest.raises(VultrTimeoutError):
            client_with(handler, max_retries=1).request("GET", "/v2/instances")


class TestRateLimiter:
    def test_second_acquire_waits_at_least_min_interval(self, monkeypatch):
        clock = {"t": 0.0}
        sleeps = []

        monkeypatch.setattr("ghostrange_vultr_control.http_client.time.monotonic", lambda: clock["t"])
        monkeypatch.setattr("ghostrange_vultr_control.http_client.time.sleep", lambda s: (sleeps.append(s), clock.__setitem__("t", clock["t"] + s)))

        limiter = _RateLimiter(requests_per_second=2.0)  # min interval 0.5s
        limiter.acquire()  # first call: no wait
        limiter.acquire()  # second call: must wait ~0.5s
        assert sleeps == [0.5]

    def test_zero_or_negative_rate_disables_limiting(self):
        limiter = _RateLimiter(requests_per_second=0)
        # should not raise / not hang
        limiter.acquire()
        limiter.acquire()
