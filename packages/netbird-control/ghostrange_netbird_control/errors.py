"""Typed exceptions for the NetBird control-plane boundary.

No raw ``httpx`` exception, and no raw HTTP status code, is ever allowed to
escape ``NetBirdClient`` / ``NetBirdHTTPClient`` to a caller. Every failure
mode is mapped to one of these. Callers (e.g. ``apps/api``'s worker
readiness gate) should catch ``NetBirdControlError`` (or a specific
subclass) — never ``httpx.HTTPError`` or ``httpx.TimeoutException``.

None of these exceptions' messages ever include the ``Authorization``
header or the raw API token. ``NetBirdHTTPClient`` only ever passes a
status code and a provider-supplied error message string into these
constructors.
"""

from __future__ import annotations

from typing import Optional


class NetBirdControlError(Exception):
    """Base class for every error this package raises."""

    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.status_code is not None:
            return f"[{self.status_code}] {self.message}"
        return self.message


class NetBirdAuthError(NetBirdControlError):
    """Missing/invalid API token, or NetBird returned 401/403.

    Also raised locally (no HTTP call made at all) when no token is
    configured — ``NetBirdClient`` never silently makes an unauthenticated
    request.
    """


class NetBirdNotFoundError(NetBirdControlError):
    """NetBird returned 404 for a resource id (peer, group, setup key)."""


class NetBirdValidationError(NetBirdControlError):
    """NetBird returned 400/422 — the request body was malformed or violated
    a NetBird-side constraint. Retrying the identical request will not
    help."""


class NetBirdRateLimitedError(NetBirdControlError):
    """NetBird returned 429 on every retry attempt and the retry budget was
    exhausted."""


class NetBirdServerError(NetBirdControlError):
    """NetBird returned a 5xx on every retry attempt and the retry budget
    was exhausted."""


class NetBirdUnavailableError(NetBirdControlError):
    """A network-level failure (DNS, connection refused/reset, TLS error)
    persisted across the retry budget."""


class NetBirdTimeoutError(NetBirdControlError):
    """A request timed out on every retry attempt, or a polling loop (the
    worker readiness gate's enrollment wait) exceeded its budget without the
    peer ever becoming connected + correctly grouped."""


__all__ = [
    "NetBirdControlError",
    "NetBirdAuthError",
    "NetBirdNotFoundError",
    "NetBirdValidationError",
    "NetBirdRateLimitedError",
    "NetBirdServerError",
    "NetBirdUnavailableError",
    "NetBirdTimeoutError",
]
