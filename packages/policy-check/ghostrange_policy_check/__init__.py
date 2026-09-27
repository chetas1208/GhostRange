"""ghostrange_policy_check: the concrete enforcement point that
docs/security/EXECUTION_POLICY.md designs but does not, by itself, code.

Public interface, the shape callers (execution-graph, adversary-adapter,
range-runtime, vultr-control) should rely on:

    from ghostrange_policy_check import PolicyCheckService, PolicyDenied
    from ghostrange_policy_check import PolicyRegistry, TokenSigner, AuditLog

    registry = PolicyRegistry()
    registry.register_range(range_id, target_set)       # range-runtime, at provisioning
    registry.register_ability("attack.discovery.host")   # reviewed-catalog onboarding
    registry.set_quota(world_id, max_cost=50.0)           # scheduler/range-runtime

    signer = TokenSigner()                                # reads GHOSTRANGE_POLICY_SIGNING_KEY
    token = signer.mint_token(world_id=..., range_id=..., target_set=..., capabilities=[...], ttl=...)

    service = PolicyCheckService(registry, signer)
    try:
        decision = service.authorize(request, token, actor=..., provenance=...)
    except PolicyDenied as exc:
        ...  # hard fail the task node; exc.decision.reason is a PolicyDenyReason

Also exported: ``ssrf_guard`` (SSRF backstop for any control-plane HTTP call
on caller-influenced host/URL input) and ``model_output_guard.resolve_target``
(the only sanctioned way model output becomes a ``TargetRef``) and
``secrets.redact_secrets`` (logging-side redaction backstop).
"""

from .audit import AuditLog
from .errors import PolicyDenied
from .model_output_guard import UnknownTargetAliasError, resolve_target
from .registry import Approval, PolicyRegistry, UnknownRangeError
from .secrets import redact_secrets
from .service import DEFAULT_TICKET_TTL, PolicyCheckService, compute_request_hash
from .signing import TokenSigner
from .ssrf_guard import SSRFBlockedError, assert_safe_egress_url, is_blocked_address

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "PolicyCheckService",
    "PolicyDenied",
    "compute_request_hash",
    "DEFAULT_TICKET_TTL",
    "PolicyRegistry",
    "UnknownRangeError",
    "Approval",
    "TokenSigner",
    "AuditLog",
    "resolve_target",
    "UnknownTargetAliasError",
    "redact_secrets",
    "assert_safe_egress_url",
    "is_blocked_address",
    "SSRFBlockedError",
]
