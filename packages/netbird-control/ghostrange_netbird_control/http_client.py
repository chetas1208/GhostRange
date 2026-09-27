"""Thin, honest HTTP wrapper around the NetBird management API.

This is the single place that:
- reads ``NETBIRD_API_TOKEN`` from the environment (never hardcoded, never
  logged, never placed in any exception message or returned record),
- sends NetBird's own auth header convention: ``Authorization: Token <token>``
  (NOT ``Bearer`` — this is NetBird's documented convention, distinct from
  the Vultr client in ``packages/vultr-control``),
- sets bounded timeouts and retries with exponential backoff + jitter on
  429/5xx/network errors, never on other 4xx (those are caller bugs),
- maps every non-2xx response (and every transport failure that survives
  the retry budget) to a typed exception from ``errors.py`` — no raw
  ``httpx`` exception or bare status code ever escapes this module.

Testability: pass ``transport=httpx.MockTransport(handler)`` to exercise
request construction and error/retry logic with zero network access and no
real credentials (see ``tests/test_http_client.py``).
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any, Optional

import httpx

from .errors import (
    NetBirdAuthError,
    NetBirdControlError,
    NetBirdNotFoundError,
    NetBirdRateLimitedError,
    NetBirdServerError,
    NetBirdTimeoutError,
    NetBirdUnavailableError,
    NetBirdValidationError,
)

logger = logging.getLogger("ghostrange.netbird_control")

DEFAULT_BASE_URL = "https://api.netbird.io"
API_TOKEN_ENV_VAR = "NETBIRD_API_TOKEN"


def _backoff_delay(attempt: int, *, base_s: float = 1.0, cap_s: float = 10.0) -> float:
    """Exponential backoff with full jitter, attempt is 1-indexed."""
    ceiling = min(cap_s, base_s * (2 ** (attempt - 1)))
    return random.uniform(0.0, ceiling)


class NetBirdHTTPClient:
    def __init__(
        self,
        api_token: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = 15.0,
        max_retries: int = 3,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        token = api_token if api_token is not None else os.environ.get(API_TOKEN_ENV_VAR)
        if not token:
            raise NetBirdAuthError(
                f"{API_TOKEN_ENV_VAR} is not set and no api_token was passed explicitly. "
                "NetBirdClient requires a real NetBird API token at runtime; it is never "
                "hardcoded or defaulted. Export NETBIRD_API_TOKEN or pass api_token= "
                "explicitly (e.g. from a secrets manager)."
            )
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_s),
            transport=transport,
            headers={
                "Authorization": f"Token {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ghostrange-netbird-control/0.1",
            },
        )
        # `token` itself is not retained as an attribute anywhere on this
        # object beyond the Authorization header already baked into
        # self._client.
        self._max_retries = max_retries

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "NetBirdHTTPClient":
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
        typed ``NetBirdControlError`` subclass on any unrecoverable
        failure."""
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self._client.request(method, path, json=json_body, params=params)
            except httpx.TimeoutException:
                if attempt > self._max_retries:
                    raise NetBirdTimeoutError(f"{method} {path} timed out after {attempt} attempt(s)")
                logger.warning("netbird-control: timeout on %s %s (attempt %d), retrying", method, path, attempt)
                time.sleep(_backoff_delay(attempt))
                continue
            except httpx.HTTPError as exc:
                if attempt > self._max_retries:
                    raise NetBirdUnavailableError(
                        f"{method} {path} failed after {attempt} attempt(s): network error ({type(exc).__name__})"
                    )
                logger.warning(
                    "netbird-control: network error on %s %s (attempt %d): %s, retrying",
                    method,
                    path,
                    attempt,
                    type(exc).__name__,
                )
                time.sleep(_backoff_delay(attempt))
                continue

            if resp.status_code == 429:
                if attempt > self._max_retries:
                    raise NetBirdRateLimitedError(
                        self._extract_error_message(resp, default="rate limited (429) — retry budget exhausted"),
                        status_code=429,
                    )
                delay = self._retry_after_delay(resp) or _backoff_delay(attempt)
                logger.warning("netbird-control: 429 on %s %s (attempt %d), backing off %.2fs", method, path, attempt, delay)
                time.sleep(delay)
                continue

            if resp.status_code >= 500:
                if attempt > self._max_retries:
                    raise NetBirdServerError(
                        self._extract_error_message(resp, default=f"HTTP {resp.status_code} — retry budget exhausted"),
                        status_code=resp.status_code,
                    )
                logger.warning("netbird-control: %d on %s %s (attempt %d), retrying", resp.status_code, method, path, attempt)
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
            raise NetBirdAuthError(message, status_code=resp.status_code)
        if resp.status_code == 404:
            raise NetBirdNotFoundError(message, status_code=resp.status_code)
        if resp.status_code in (400, 422):
            raise NetBirdValidationError(message, status_code=resp.status_code)
        raise NetBirdControlError(message, status_code=resp.status_code)

    @staticmethod
    def _extract_error_message(resp: httpx.Response, *, default: str) -> str:
        try:
            data = resp.json()
        except ValueError:
            return default
        if isinstance(data, dict):
            for key in ("message", "error", "detail"):
                if key in data:
                    return str(data[key])
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


__all__ = ["NetBirdHTTPClient", "DEFAULT_BASE_URL", "API_TOKEN_ENV_VAR"]
