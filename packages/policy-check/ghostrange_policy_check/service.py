"""The enforcement point: ``PolicyCheckService.authorize()``.

Implements EXECUTION_POLICY.md §3.2's seven checks, in order, exactly:

    1. token integrity (signature, expiry, world/range scope match)
    2. re-derive canonical target set from the registry, check subset
    3. capability check (token grants this action_category)
    4. ability catalog check (T11 — only reviewed abilities)
    5. quota check (T13)
    6. human-approval-required categories (T15, §7)
    7. absolute off-range deny (redundant with #2 by construction — there
       is no ALLOW branch this could ever reach if #2 already denied)

On ANY failure — expected policy violation or unexpected internal error —
this raises ``PolicyDenied``. There is no code path that returns a falsy-
but-ignorable value, and no "assume allowed if something downstream is
unreachable" branch (EXECUTION_POLICY.md §3.3): an unexpected exception
from the registry or signer is caught and converted into a
``POLICY_SERVICE_UNAVAILABLE`` deny, not re-raised as some other exception
type a caller might not think to catch.

Interface for callers (execution-graph, adversary-adapter, range-runtime,
vultr-control):

    from ghostrange_policy_check import PolicyCheckService, PolicyDenied

    service = PolicyCheckService(registry, signer)
    try:
        decision = service.authorize(request, token, actor=..., provenance=...)
    except PolicyDenied as exc:
        # exc.decision.reason is a PolicyDenyReason -- hard fail the task
        # node here. Do not retry with different wording.
        raise
    # decision.ticket is the short-lived, single-use execution-authorization
    # ticket -- pass it to the executor, which independently re-verifies it
    # (signer.verify_ticket) immediately before its side-effecting call.
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import NoReturn, Optional

from ghostrange_contracts._base import Id
from ghostrange_contracts.enums import PolicyDenyReason
from ghostrange_contracts.policy import (
    ActorRef,
    ExecutionRequestV1,
    PolicyDecisionV1,
    ProvenanceRef,
    RangeOwnershipTokenV1,
)

from .audit import AuditLog
from .errors import PolicyDenied
from .registry import PolicyRegistry, UnknownRangeError
from .signing import TokenSigner

DEFAULT_TICKET_TTL = timedelta(seconds=60)


def compute_request_hash(request: ExecutionRequestV1) -> str:
    """Deterministic hash of a request's full contents. Used both as the
    ticket's hash-binding and as the audit log's cross-reference key. The
    check is per-request-hash, not per-task_id, so renaming/retrying under
    a new task_id does not let a denied request slip through unchecked
    (EXECUTION_POLICY.md §3.2 closing note).
    """
    payload = request.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PolicyCheckService:
    """One instance wraps one registry + one signer + one audit log. In a
    real deployment this is the process behind the "separate deployable
    component" EXECUTION_POLICY.md §1 describes, reachable only via
    authenticated internal RPC; this class is that process's actual
    decision logic, callable directly in-process for M2 and wrappable
    behind an RPC handler later without changing this interface.
    """

    def __init__(
        self,
        registry: PolicyRegistry,
        signer: TokenSigner,
        audit_log: Optional[AuditLog] = None,
        *,
        ticket_ttl: timedelta = DEFAULT_TICKET_TTL,
    ) -> None:
        self.registry = registry
        self.signer = signer
        self.audit_log = audit_log if audit_log is not None else AuditLog()
        self.ticket_ttl = ticket_ttl

    def authorize(
        self,
        request: ExecutionRequestV1,
        token: RangeOwnershipTokenV1,
        *,
        actor: ActorRef,
        provenance: ProvenanceRef,
    ) -> PolicyDecisionV1:
        """Run every check; return an ALLOW ``PolicyDecisionV1`` (carrying
        a ticket) or raise ``PolicyDenied`` (carrying a DENY decision).
        Every outcome, allow or deny, is appended to ``self.audit_log``
        before this returns/raises.
        """
        req_hash = compute_request_hash(request)

        def deny(reason: PolicyDenyReason) -> NoReturn:
            self.audit_log.append(
                actor=actor,
                request_hash=req_hash,
                decision="DENY",
                reason=reason,
                world_id=request.world_id,
                range_id=request.range_id,
                target_refs=request.target_refs,
                provenance=provenance,
                signing_key=self.signer.key,
            )
            decision = PolicyDecisionV1(
                allowed=False, reason=reason, request_hash=req_hash, ticket=None
            )
            raise PolicyDenied(decision)

        try:
            # --- step 1: token integrity -----------------------------------
            if not self.signer.verify_token(token):
                deny(PolicyDenyReason.BAD_TOKEN_SIGNATURE)
            if token.is_expired:
                deny(PolicyDenyReason.TOKEN_EXPIRED)
            if token.world_id != request.world_id or token.range_id != request.range_id:
                deny(PolicyDenyReason.TOKEN_SCOPE_MISMATCH)

            # --- step 2: re-derive canonical truth, never trust the request
            try:
                canonical_targets = self.registry.get_target_set(request.range_id)
            except UnknownRangeError:
                deny(PolicyDenyReason.UNKNOWN_RANGE)

            canonical_set = {(t.range_id, t.host_or_ip) for t in canonical_targets}
            requested_set = {(t.range_id, t.host_or_ip) for t in request.target_refs}
            if not requested_set <= canonical_set:
                deny(PolicyDenyReason.TARGET_NOT_IN_RANGE)

            # --- step 3: capability check -----------------------------------
            if request.action_category not in token.capabilities:
                deny(PolicyDenyReason.CAPABILITY_NOT_GRANTED)

            # --- step 4: ability catalog check (T11) ------------------------
            if not self.registry.is_reviewed_ability(request.ability_ref):
                deny(PolicyDenyReason.ABILITY_NOT_IN_CATALOG)

            # --- step 5: quota check (T13) -----------------------------------
            if not self.registry.admit_quota(request.world_id, request.resource_cost):
                deny(PolicyDenyReason.QUOTA_EXCEEDED)

            # --- step 6: human-approval-required categories (T15, §7) -------
            if request.action_category in self.registry.human_approval_required_categories:
                approval = self.registry.get_approval(req_hash)
                if approval is None or approval.is_expired:
                    deny(PolicyDenyReason.HUMAN_APPROVAL_REQUIRED)

            # --- step 7: absolute off-range deny (redundant with #2; there is
            # no code path that reaches here with an off-range target, by
            # construction of step 2 above -- restated per EXECUTION_POLICY.md
            # §3.2 step 7 as an explicit, uncatchable non-branch, not merely
            # an assumption) ---------------------------------------------------
            if not requested_set <= canonical_set:
                deny(PolicyDenyReason.OFF_RANGE_TARGET_ABSOLUTE_DENY)

        except PolicyDenied:
            raise
        except Exception as exc:  # noqa: BLE001 -- fail-closed: ANY unexpected
            # error (registry unreachable, malformed data, etc.) is a deny,
            # never a silent pass-through (EXECUTION_POLICY.md §3.3).
            self.audit_log.append(
                actor=actor,
                request_hash=req_hash,
                decision="DENY",
                reason=PolicyDenyReason.POLICY_SERVICE_UNAVAILABLE,
                world_id=request.world_id,
                range_id=request.range_id,
                target_refs=request.target_refs,
                provenance=provenance,
                signing_key=self.signer.key,
            )
            decision = PolicyDecisionV1(
                allowed=False,
                reason=PolicyDenyReason.POLICY_SERVICE_UNAVAILABLE,
                request_hash=req_hash,
                ticket=None,
            )
            raise PolicyDenied(decision) from exc

        ticket = self.signer.issue_ticket(req_hash, ttl=self.ticket_ttl)
        self.audit_log.append(
            actor=actor,
            request_hash=req_hash,
            decision="ALLOW",
            reason=None,
            world_id=request.world_id,
            range_id=request.range_id,
            target_refs=request.target_refs,
            provenance=provenance,
            signing_key=self.signer.key,
        )
        return PolicyDecisionV1(allowed=True, reason=None, request_hash=req_hash, ticket=ticket)


__all__ = ["PolicyCheckService", "compute_request_hash", "DEFAULT_TICKET_TTL"]
