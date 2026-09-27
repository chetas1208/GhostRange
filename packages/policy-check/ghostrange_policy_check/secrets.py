"""Structured-logging redaction backstop (EXECUTION_POLICY.md §6): "No
secret is ever logged, and the audit log is checked in code review to
confirm request/response bodies it captures for provenance never include
credential fields (structured logging with an explicit secret-redaction
allowlist of field names, fail-closed: unknown fields are redacted by
default, not passed through by default)."

This is explicitly a SECOND line of defense, not the real control. The
real control is architectural: range-runtime/vultr-control/adversary-
adapter never read secrets into range-accessible structures in the first
place (T4), and this M2 audit found no code in packages/vultr-control or
packages/range-runtime at all yet — both directories are still empty, so
there is currently nothing there that could log a secret. This helper is
what those packages MUST route any dict-shaped log line through once they
exist, so the property holds by construction rather than by every future
call site remembering to be careful.

Fail-closed direction, restated in code: ``redact_secrets`` denylists
*known* secret-shaped field names. It does NOT allowlist safe fields —
this is a deliberate, narrower guarantee than "fail-closed" would mean for
the real credential-custody control (T4/§6's actual answer there is
"never let the secret exist in a loggable place," not "hope the redaction
list is complete"). Treat this as a courtesy net for accidental inclusion,
never as the reason it's safe to pass a raw secrets-manager response
through a generic logger.
"""

from __future__ import annotations

from typing import Any

# Deliberately specific compound markers, not bare words like "token" or
# "key" (a bare "token" denylist entry would over-redact legitimate,
# non-secret fields such as token_id/ticket_id/request_hash-adjacent
# bookkeeping, which are useful in logs and are not credentials).
_SECRET_FIELD_MARKERS = (
    "api_key",
    "apikey",
    "password",
    "passwd",
    "secret",
    "credential",
    "private_key",
    "signing_key",
    "admin_key",
    "operator_key",
    "enrollment_token",
    "db_password",
    "auth_token",
    "access_token",
    "bearer",
    "connection_string",
)

REDACTED = "***REDACTED***"


def _is_secret_shaped(field_name: str) -> bool:
    lowered = field_name.lower()
    return any(marker in lowered for marker in _SECRET_FIELD_MARKERS)


def redact_secrets(data: Any) -> Any:
    """Recursively walk ``data`` (expected to be a JSON-shaped dict/list
    from ``model_dump`` or similar) and replace the value of any key whose
    name matches a known secret-shaped marker with ``REDACTED``. Safe to
    call on anything JSON-shaped; non-dict/list leaves are returned as-is.
    """
    if isinstance(data, dict):
        result: dict[str, Any] = {}
        for key, value in data.items():
            if _is_secret_shaped(str(key)):
                result[key] = REDACTED
            else:
                result[key] = redact_secrets(value)
        return result
    if isinstance(data, list):
        return [redact_secrets(item) for item in data]
    return data


__all__ = ["redact_secrets", "REDACTED"]
