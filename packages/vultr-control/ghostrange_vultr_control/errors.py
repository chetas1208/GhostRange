"""Typed exceptions for the Vultr control-plane boundary.

No raw ``httpx`` exception, and no raw HTTP status code, is ever allowed to
escape ``RealVultrProvider`` / ``VultrHTTPClient`` to a caller. Every failure
mode is mapped to one of these. Callers in ``packages/range-runtime`` /
``packages/range-iac`` should catch ``VultrControlError`` (or a specific
subclass) — never ``httpx.HTTPError`` or ``httpx.TimeoutException``.

None of these exceptions' messages ever include the ``Authorization`` header
or the raw API key. ``VultrHTTPClient`` only ever passes a status code and a
provider-supplied error message string into these constructors.
"""

from __future__ import annotations

from typing import Optional


class VultrControlError(Exception):
    """Base class for every error this package raises."""

    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.status_code is not None:
            return f"[{self.status_code}] {self.message}"
        return self.message


class VultrAuthError(VultrControlError):
    """Missing/invalid API key, or Vultr returned 401/403.

    Also raised locally (no HTTP call made at all) when ``VULTR_API_KEY`` is
    not set and no explicit ``api_key=`` was passed to ``RealVultrProvider``.
    """


class VultrNotFoundError(VultrControlError):
    """Vultr returned 404 for a resource id — or, during a destroy-and-confirm
    poll loop, this is the *success* signal (resource is actually gone)."""


class VultrValidationError(VultrControlError):
    """Vultr returned 400/422 — the request body was malformed or violated a
    Vultr-side constraint. Retrying the identical request will not help."""


class VultrConflictError(VultrControlError):
    """Vultr returned 409 — the resource is in a state that conflicts with
    the requested operation (e.g. deleting an instance mid-provision)."""


class VultrRateLimitedError(VultrControlError):
    """Vultr returned 429 on every retry attempt (rate limit is ~30 req/s per
    source IP, per Vultr's own docs) and the retry budget was exhausted."""


class VultrServerError(VultrControlError):
    """Vultr returned a 5xx on every retry attempt and the retry budget was
    exhausted."""


class VultrUnavailableError(VultrControlError):
    """A network-level failure (DNS, connection refused/reset, TLS error)
    persisted across the retry budget — Vultr's API could not be reached at
    all, as distinct from Vultr reachably returning an error."""


class VultrTimeoutError(VultrControlError):
    """A request timed out on every retry attempt, or a polling loop
    (``wait_until_ready`` / destroy-and-confirm) exceeded its budget without
    reaching the expected terminal state."""


__all__ = [
    "VultrControlError",
    "VultrAuthError",
    "VultrNotFoundError",
    "VultrValidationError",
    "VultrConflictError",
    "VultrRateLimitedError",
    "VultrServerError",
    "VultrUnavailableError",
    "VultrTimeoutError",
]
