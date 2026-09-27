"""Typed M2 execution actions — no free-form shell from model output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class HttpRequestResult:
    method: str
    url: str
    status_code: int
    body_excerpt: str
    headers: dict[str, str]


def run_auth_validation_http(*, base_url: str | None, simulate: bool) -> HttpRequestResult:
    """Controlled auth-lab check: bad credential must be rejected (401/403)."""
    if simulate or not base_url:
        return HttpRequestResult(
            method="GET",
            url=f"{base_url or 'http://auth-lab.local'}/auth/validate",
            status_code=401,
            body_excerpt="401 Unauthorized — expected unsafe condition reproduced",
            headers={"content-type": "application/json"},
        )
    import urllib.error
    import urllib.request

    url = f"{base_url.rstrip('/')}/auth/validate"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read(4096).decode("utf-8", errors="replace")
            return HttpRequestResult("GET", url, resp.status, body[:500], dict(resp.headers))
    except urllib.error.HTTPError as exc:
        body = exc.read(4096).decode("utf-8", errors="replace")
        return HttpRequestResult("GET", url, exc.code, body[:500], dict(exc.headers))


ActionKind = Literal["health_check", "http_request", "config_inspection", "verification"]
