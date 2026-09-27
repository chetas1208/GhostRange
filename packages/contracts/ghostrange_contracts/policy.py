"""Policy and Budget: the two levers that bound what agents/scheduler may do.

Policy is the allowlist/denylist enforced by the security-boundary policy-
check service (``docs/security/EXECUTION_POLICY.md``) — architectural, not
prompt-based: execution-graph consults this before dispatching any Task.
Budget is the cost/time envelope GhostScheduler must respect; exhausting it
is itself a first-class scheduler reason code (``BUDGET_EXHAUSTED``).

This module also carries the concrete data shapes EXECUTION_POLICY.md
names but left as "conceptually, final shape lives in packages/contracts"
(§2): ``TargetRef``, ``RangeOwnershipTokenV1``, ``ExecutionRequestV1``,
``ExecutionTicketV1``, ``PolicyDecisionV1``, ``ActorRef``,
``ProvenanceRef``, ``AuditRecordV1``. The enforcement *logic* that consumes
these (the ``authorize()`` function, token signing, the registry, the
audit-log writer) lives in the separate ``packages/policy-check`` package —
this module only owns their *shape*, per the project's existing
contracts/logic split (see module docstring in ``execution_graph.py``).

Added by Agent 05 (Security Boundary Engineer) for M2. Per
``docs/milestones/M2_COORDINATION.md``'s contract-change protocol, this is
an ADDITIVE-only change (no existing field on ``PolicyV1``/``BudgetV1`` was
touched) flagged in that agent's report for the lead to reconcile against
any other in-flight proposal to this shared file.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import Field, field_validator, model_validator

from ._base import AwareDatetime, GhostRangeModel, Id, VersionedModel, new_id, utc_now
from .enums import AbilityCategory, PolicyActorKind, PolicyDenyReason


class PolicyV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    name: str
    description: str = ""
    allowed_actions: list[str] = Field(
        default_factory=list,
        description="Allowlist of action identifiers permitted under this policy; "
        "empty means nothing is permitted by default (explicit deny-by-default)",
    )
    denied_actions: list[str] = Field(
        default_factory=list,
        description="Explicit denylist; always takes precedence over allowed_actions",
    )
    require_range_ownership_token: bool = Field(
        default=True,
        description="If True, every action under this policy must present a valid "
        "range-ownership token proving the target environment is GhostRange-owned",
    )
    created_at: AwareDatetime = Field(default_factory=utc_now)

    def permits(self, action: str) -> bool:
        """Evaluate deny-overrides-allow, deny-by-default for this policy."""
        if action in self.denied_actions:
            return False
        return action in self.allowed_actions


class BudgetV1(VersionedModel):
    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    id: Id = Field(default_factory=new_id)
    range_id: Id
    max_total_cost_usd: float = Field(..., gt=0)
    spent_cost_usd: float = Field(default=0, ge=0)
    max_duration_seconds: float = Field(..., gt=0)
    alert_threshold_pct: float = Field(default=0.8, ge=0, le=1)
    hard_stop: bool = Field(
        default=True, description="If True, scheduler must refuse new spend once exhausted"
    )
    created_at: AwareDatetime = Field(default_factory=utc_now)

    # Note: spent_cost_usd is intentionally allowed to exceed max_total_cost_usd
    # (the task that tips a budget over is still recorded honestly) — callers
    # must check is_exhausted() rather than relying on validation to prevent
    # overspend after the fact.

    @property
    def is_exhausted(self) -> bool:
        return self.spent_cost_usd >= self.max_total_cost_usd

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.max_total_cost_usd - self.spent_cost_usd)


# ---------------------------------------------------------------------------
# Range-ownership token & the authorize() request/response shapes
# (docs/security/EXECUTION_POLICY.md §2-3, §8)
# ---------------------------------------------------------------------------


class TargetRef(GhostRangeModel):
    """A single execution target, scoped to exactly one range.

    Deliberately NOT free text with no constraint: ``host_or_ip`` must be a
    plausible bare hostname or IPv4/IPv6 literal (no scheme, no path, no
    whitespace, no shell/URL metacharacters) so this type can never itself
    become an injection vector even before the *semantic* check ("is this
    actually in the range's registry") runs in policy-check. The semantic
    check is the real security property (enforced by
    ``packages/policy-check``, re-derived from its own registry on every
    call) — this pattern constraint is defense-in-depth, not a substitute
    for it.
    """

    range_id: Id
    host_or_ip: str = Field(..., min_length=1, max_length=253)

    @field_validator("host_or_ip")
    @classmethod
    def _no_injection_shaped_text(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"[A-Za-z0-9.:_-]+", v):
            raise ValueError(
                "host_or_ip must be a bare hostname/IP literal "
                "(no scheme, path, query, or whitespace)"
            )
        return v


class RangeOwnershipTokenV1(VersionedModel):
    """Proof that a (world, range) pair is a real, currently-active,
    GhostRange-owned environment with a specific capability set — the
    credential named throughout THREAT_MODEL.md (T5, T9, T10, T16) and
    specified in EXECUTION_POLICY.md §2.

    Minted exclusively by range-runtime at provisioning time (never by an
    agent, never on demand for a wider scope — there is no
    "mint-a-token" endpoint anywhere). ``target_set`` is always the real,
    just-provisioned member list, never aspirational. Signature custody and
    minting/verification logic live in ``packages/policy-check`` (this
    class only defines the wire shape); ``issuer_signature`` here is
    opaque to this module by design.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    token_id: Id = Field(default_factory=new_id)
    world_id: Id
    range_id: Id
    target_set: list[TargetRef] = Field(default_factory=list)
    capabilities: list[AbilityCategory] = Field(default_factory=list)
    issued_at: AwareDatetime = Field(default_factory=utc_now)
    expires_at: AwareDatetime
    issuer_signature: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _expiry_after_issuance(self) -> "RangeOwnershipTokenV1":
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be strictly after issued_at")
        return self

    @property
    def is_expired(self) -> bool:
        """Cheap, signature-independent expiry check. ``authorize()`` still
        must call this (never infer non-expiry from the mere fact that a
        caller "has" a token) — see EXECUTION_POLICY.md §3.2 step 1.
        """
        return utc_now() >= self.expires_at


_TARGET_LIKE_PARAM_KEYS = frozenset(
    {"host", "hosts", "ip", "ips", "url", "urls", "target", "targets",
     "hostname", "hostnames", "address", "addresses", "endpoint",
     "endpoints", "uri", "uris", "destination"}
)


class ExecutionRequestV1(VersionedModel):
    """The concrete input to ``authorize()`` (EXECUTION_POLICY.md §3.1-3.2).

    ``target_refs`` is fixed at DAG-compile time by execution-graph, never
    widened by agent reasoning about a specific node (T10). ``params`` is
    ability-parameter-only: the validator below rejects any key that looks
    like it is smuggling a target/host/URL through the parameters channel,
    as a second, independent backstop alongside ``target_refs`` being the
    only sanctioned way a target enters a request.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    request_id: Id = Field(default_factory=new_id)
    task_id: Id
    world_id: Id
    range_id: Id
    target_refs: list[TargetRef] = Field(..., min_length=1)
    action_category: AbilityCategory
    ability_ref: str = Field(
        ..., min_length=1,
        description="Must resolve against the reviewed CALDERA ability catalog (T11) — "
        "never an inline/novel ability body.",
    )
    params: dict = Field(default_factory=dict)
    resource_cost: float = Field(default=0.0, ge=0)
    requested_by: str = Field(
        ..., description="Agent tool-call id / task provenance string for the audit trail"
    )
    requested_at: AwareDatetime = Field(default_factory=utc_now)

    @field_validator("params")
    @classmethod
    def _params_never_carry_targets(cls, v: dict) -> dict:
        bad = _TARGET_LIKE_PARAM_KEYS & {str(k).lower() for k in v}
        if bad:
            raise ValueError(
                f"params must not carry target-like keys {sorted(bad)!r}; "
                "targets must be declared via target_refs, never smuggled through params"
            )
        return v

    @model_validator(mode="after")
    def _targets_share_this_requests_range(self) -> "ExecutionRequestV1":
        for ref in self.target_refs:
            if ref.range_id != self.range_id:
                raise ValueError(
                    f"target_ref.range_id {ref.range_id} does not match "
                    f"request.range_id {self.range_id}"
                )
        return self


class ExecutionTicketV1(VersionedModel):
    """Short-lived, single-use, request-hash-bound authorization ticket
    issued on ALLOW (EXECUTION_POLICY.md §3.4). Executors
    (adversary-adapter, range-runtime, vultr-control) re-verify this
    ticket's signature and hash-binding themselves, immediately before
    their side-effecting call — a policy-check ALLOW decision is not
    itself permission to act.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    ticket_id: Id = Field(default_factory=new_id)
    request_hash: str = Field(..., min_length=1)
    issued_at: AwareDatetime = Field(default_factory=utc_now)
    expires_at: AwareDatetime
    single_use: bool = True
    signature: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _expiry_after_issuance(self) -> "ExecutionTicketV1":
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be strictly after issued_at")
        return self


class PolicyDecisionV1(VersionedModel):
    """The structured, terminal result of one ``authorize()`` call.

    Shape-enforced consistency (not just convention): an ALLOW decision
    always carries a ticket and never a reason; a DENY decision always
    carries a reason and never a ticket. This makes "allowed=True but no
    ticket" or "allowed=False but here's a ticket anyway" a construction-
    time error, not a bug some caller could introduce later.
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    allowed: bool
    reason: Optional[PolicyDenyReason] = None
    request_hash: str = Field(..., min_length=1)
    ticket: Optional[ExecutionTicketV1] = None
    decided_at: AwareDatetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _allow_deny_shape(self) -> "PolicyDecisionV1":
        if self.allowed:
            if self.ticket is None:
                raise ValueError("an ALLOW decision must carry an execution ticket")
            if self.reason is not None:
                raise ValueError("an ALLOW decision must not carry a deny reason")
        else:
            if self.reason is None:
                raise ValueError("a DENY decision must carry a reason code")
            if self.ticket is not None:
                raise ValueError("a DENY decision must not carry a ticket")
        return self


class ActorRef(GhostRangeModel):
    """Who/what issued the request that produced an ``AuditRecordV1``."""

    kind: PolicyActorKind
    id: str = Field(..., min_length=1)
    tool_call_id: Optional[str] = None


class ProvenanceRef(GhostRangeModel):
    """Code-level provenance for an ``AuditRecordV1``: which package/version
    issued the request and which DAG node it was for.
    """

    package: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    dag_node_id: Optional[Id] = None


class AuditRecordV1(VersionedModel):
    """One immutable, hash-chained record of an authorize() decision
    (EXECUTION_POLICY.md §8). ``prev_hash`` chains to the previous record's
    ``signature`` — append-only by construction of the chain, not merely by
    storage-layer convention (the storage-layer backstop, a DB role with no
    UPDATE/DELETE grant, is a deployment concern outside this shape).
    """

    SCHEMA_VERSION: ClassVar[str] = "1"
    schema_version: Literal["1"] = "1"

    seq: int = Field(..., ge=0)
    prev_hash: str = Field(..., min_length=1)
    timestamp: AwareDatetime = Field(default_factory=utc_now)
    actor: ActorRef
    request_hash: str = Field(..., min_length=1)
    decision: Literal["ALLOW", "DENY"]
    reason: Optional[PolicyDenyReason] = None
    world_id: Id
    range_id: Optional[Id] = None
    target_refs: list[TargetRef] = Field(default_factory=list)
    provenance: ProvenanceRef
    signature: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _reason_matches_decision(self) -> "AuditRecordV1":
        if self.decision == "DENY" and self.reason is None:
            raise ValueError("a DENY audit record must carry a reason code")
        if self.decision == "ALLOW" and self.reason is not None:
            raise ValueError("an ALLOW audit record must not carry a deny reason")
        return self


__all__ = [
    "PolicyV1",
    "BudgetV1",
    "TargetRef",
    "RangeOwnershipTokenV1",
    "ExecutionRequestV1",
    "ExecutionTicketV1",
    "PolicyDecisionV1",
    "ActorRef",
    "ProvenanceRef",
    "AuditRecordV1",
]
