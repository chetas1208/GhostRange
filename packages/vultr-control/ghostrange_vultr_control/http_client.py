"""Thin, honest HTTP wrapper around Vultr API v2.

This is the single place that:
- reads ``VULTR_API_KEY`` from the environment (never hardcoded, never
  logged, never placed in any exception message or returned record),
- sets bounded connect/read/write/pool timeouts,
- retries with exponential backoff + jitter on 429 (rate-limited — Vultr
  documents ~30 requests/second per source IP) and on 5xx/network errors,
  never on other 4xx (those are caller bugs; retrying an invalid request
  will not fix it),
- proactively self-throttles below Vultr's documented limit via a simple
  leaky-bucket rate limiter, so a single ``RealVultrProvider`` instance
  cannot itself trip the 429 in normal use,
- maps every non-2xx response (and every transport failure that survives
  the retry budget) to a typed exception from ``errors.py`` — no raw
  ``httpx`` exception or bare status code ever escapes this module.

Testability: pass ``transport=httpx.MockTransport(handler)`` to exercise
request construction and error/retry logic with zero network access and no
real credentials (see ``tests/test_http_client.py`` and
``tests/test_real_provider_requests.py``).
"""

from __future__ import annotations

import logging
import os
import random
import threading
import time
from typing import Any, Optional

import httpx

from .errors import (
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

logger = logging.getLogger("ghostrange.vultr_control")

DEFAULT_BASE_URL = "https://api.vultr.com"
API_KEY_ENV_VAR = "VULTR_API_KEY"


class _RateLimiter:
    """Simple leaky-bucket-of-one: never issue two requests closer together
    than ``1 / requests_per_second``. Thread-safe. This is a client-side
    self-throttle, not a substitute for handling 429 — Vultr's limit is
    per-*IP*, so other processes sharing the same egress IP can still cause
    429s this limiter cannot see."""

    def __init__(self, requests_per_second: float) -> None:
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self._last_request_at: Optional[float] = None
        self._lock = threading.Lock()

    def acquire(self) -> None:
        if self._min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            if self._last_request_at is None:
                self._last_request_at = now
                return
            wait = self._last_request_at + self._min_interval - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._last_request_at = now


def _backoff_delay(attempt: int, *, base_s: float = 1.0, cap_s: float = 20.0) -> float:
    """Exponential backoff with full jitter, attempt is 1-indexed."""
    ceiling = min(cap_s, base_s * (2 ** (attempt - 1)))
    return random.uniform(0.0, ceiling)


class VultrHTTPClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = 30.0,
        max_retries: int = 5,
        requests_per_second: float = 15.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get(API_KEY_ENV_VAR)
        if not key:
            raise VultrAuthError(
                f"{API_KEY_ENV_VAR} is not set and no api_key was passed explicitly. "
                "RealVultrProvider requires a real Vultr API key at runtime; it is "
                "never hardcoded or defaulted. Export VULTR_API_KEY or pass "
                "api_key= explicitly (e.g. from a secrets manager)."
            )
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_s),
            transport=transport,
            headers={
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ghostrange-vultr-control/0.1",
            },
        )
        # `key` itself is not retained as an attribute anywhere on this
        # object beyond the Authorization header already baked into
        # self._client — minimizes the surface that could ever accidentally
        # get logged, repr'd, or serialized.
        self._max_retries = max_retries
        self._rate_limiter = _RateLimiter(requests_per_second)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "VultrHTTPClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Issue one logical request, retrying transparently on 429/5xx/
        network errors up to ``max_retries`` additional attempts. Returns
        the parsed JSON body (or ``None`` for a 204/empty body). Raises a
        typed ``VultrControlError`` subclass on any unrecoverable failure.
        """
        attempt = 0
        while True:
            attempt += 1
            self._rate_limiter.acquire()
            try:
                resp = self._client.request(method, path, json=json_body, params=params)
            except httpx.TimeoutException:
                if attempt > self._max_retries:
                    raise VultrTimeoutError(f"{method} {path} timed out after {attempt} attempt(s)")
                logger.warning("vultr-control: timeout on %s %s (attempt %d), retrying", method, path, attempt)
                time.sleep(_backoff_delay(attempt))
                continue
            except httpx.HTTPError as exc:
                if attempt > self._max_retries:
                    raise VultrUnavailableError(
                        f"{method} {path} failed after {attempt} attempt(s): network error ({type(exc).__name__})"
                    )
                logger.warning(
                    "vultr-control: network error on %s %s (attempt %d): %s, retrying",
                    method,
                    path,
                    attempt,
                    type(exc).__name__,
                )
                time.sleep(_backoff_delay(attempt))
                continue

            if resp.status_code == 429:
                if attempt > self._max_retries:
                    raise VultrRateLimitedError(
                        self._extract_error_message(resp, default="rate limited (429) — retry budget exhausted"),
                        status_code=429,
                    )
                delay = self._retry_after_delay(resp) or _backoff_delay(attempt)
                logger.warning("vultr-control: 429 on %s %s (attempt %d), backing off %.2fs", method, path, attempt, delay)
                time.sleep(delay)
                continue

            if resp.status_code >= 500:
                if attempt > self._max_retries:
                    raise VultrServerError(
                        self._extract_error_message(resp, default=f"HTTP {resp.status_code} — retry budget exhausted"),
                        status_code=resp.status_code,
                    )
                logger.warning("vultr-control: %d on %s %s (attempt %d), retrying", resp.status_code, method, path, attempt)
                time.sleep(_backoff_delay(attempt))
                continue

            return self._finish(resp, method, path)

    # -- response handling -------------------------------------------------

    def _finish(self, resp: httpx.Response, method: str, path: str) -> Any:
        if 200 <= resp.status_code < 300:
            if resp.status_code in (204, 205) or not resp.content:
                return None
            try:
                return resp.json()
            except ValueError:
                return None

        message = self._extract_error_message(resp, default=f"HTTP {resp.status_code} on {method} {path}")
        if resp.status_code in (401, 403):
            raise VultrAuthError(message, status_code=resp.status_code)
        if resp.status_code == 404:
            raise VultrNotFoundError(message, status_code=resp.status_code)
        if resp.status_code == 409:
            raise VultrConflictError(message, status_code=resp.status_code)
        if resp.status_code in (400, 422):
            raise VultrValidationError(message, status_code=resp.status_code)
        raise VultrControlError(message, status_code=resp.status_code)

    @staticmethod
    def _extract_error_message(resp: httpx.Response, *, default: str) -> str:
        try:
            data = resp.json()
        except ValueError:
            return default
        if isinstance(data, dict) and "error" in data:
            return str(data["error"])
        return default

    @staticmethod
    def _retry_after_delay(resp: httpx.Response) -> Optional[float]:
        raw = resp.headers.get("Retry-After")
        if not raw:
            return None
        try:
            return max(0.0, float(raw))
        except ValueError:
            return None


__all__ = ["VultrHTTPClient", "DEFAULT_BASE_URL", "API_KEY_ENV_VAR"]
