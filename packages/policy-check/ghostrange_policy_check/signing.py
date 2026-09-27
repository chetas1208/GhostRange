"""Token/ticket minting and verification (EXECUTION_POLICY.md §2, §3.4).

Custody rule, restated from the doc and enforced by this module's shape,
not just its docstring: the signing key lives ONLY inside a ``TokenSigner``
instance, is never a field on any contract model (``RangeOwnershipTokenV1``
carries a signature, never the key), and this module never logs, prints,
or serializes ``self._key`` anywhere. Pair this with
``ghostrange_policy_check.secrets.redact_secrets`` for the logging-side
backstop in any caller code that logs request/response dicts.

M2 stub uses HMAC-SHA256 over canonical (sorted-key) JSON of the signed
fields. This is a real cryptographic signature (not a placeholder string),
just not the production KMS/JWT-issuer EXECUTION_POLICY.md §2 describes as
the eventual home ("HMAC/JWT signature; signing key held only by
range-runtime + policy-check"). Swapping the MAC construction for a KMS-
backed one later does not change this module's public interface.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import timedelta

from ghostrange_contracts._base import Id, new_id, utc_now
from ghostrange_contracts.enums import AbilityCategory
from ghostrange_contracts.policy import (
    ExecutionTicketV1,
    RangeOwnershipTokenV1,
    TargetRef,
)

_MIN_KEY_BYTES = 16


class TokenSigner:
    """Mints and verifies ``RangeOwnershipTokenV1`` and
    ``ExecutionTicketV1`` instances. One signer instance = one signing key
    = one trust domain; policy-check and range-runtime must be configured
    with the same key material (out of band — this module does not
    distribute keys).
    """

    ENV_VAR = "GHOSTRANGE_POLICY_SIGNING_KEY"

    def __init__(self, key: bytes | None = None):
        if key is None:
            env_val = os.environ.get(self.ENV_VAR)
            if not env_val:
                raise RuntimeError(
                    f"no signing key provided and {self.ENV_VAR} is not set; "
                    "refusing to fabricate one silently (fail closed, not "
                    "fail open with an implicit default key)"
                )
            key = env_val.encode()
        if len(key) < _MIN_KEY_BYTES:
            raise ValueError(
                f"signing key must be at least {_MIN_KEY_BYTES} bytes; refusing a weak key"
            )
        self._key = key

    # -- internal MAC plumbing --------------------------------------------

    def _mac(self, payload: str) -> str:
        return hmac.new(self._key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _canonical(fields: dict) -> str:
        return json.dumps(fields, sort_keys=True, default=str)

    @property
    def key(self) -> bytes:
        """Exposed only so ``AuditLog`` (same trust boundary, same process)
        can sign audit records with the same key material. This is not a
        public "read the secret out" API for arbitrary callers — nothing
        outside this package's own service/audit modules should touch it,
        and it must never be logged.
        """
        return self._key

    # -- RangeOwnershipTokenV1 ---------------------------------------------

    def _token_fields(
        self,
        *,
        token_id: Id,
        world_id: Id,
        range_id: Id,
        target_set: list[TargetRef],
        capabilities: list[AbilityCategory],
        issued_at,
        expires_at,
    ) -> dict:
        return {
            "token_id": str(token_id),
            "world_id": str(world_id),
            "range_id": str(range_id),
            "target_set": [t.model_dump(mode="json") for t in target_set],
            "capabilities": [c.value for c in capabilities],
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

    def mint_token(
        self,
        *,
        world_id: Id,
        range_id: Id,
        target_set: list[TargetRef],
        capabilities: list[AbilityCategory],
        ttl: timedelta,
        issued_at=None,
    ) -> RangeOwnershipTokenV1:
        """The ONLY sanctioned way a ``RangeOwnershipTokenV1`` comes into
        existence. Callable only by whatever plays the role of
        range-runtime's provisioning pipeline — there is no agent-reachable
        wrapper around this anywhere in the system.

        ``issued_at`` defaults to now; it exists as an explicit override
        only so tests can mint an already-expired token (both
        ``issued_at``/``expires_at`` in the past, still ``expires_at >
        issued_at`` so the contract's own ordering validator is satisfied)
        without faking a signature by hand. Production callers should not
        pass it.
        """
        issued_at = issued_at if issued_at is not None else utc_now()
        expires_at = issued_at + ttl
        token_id = new_id()
        fields = self._token_fields(
            token_id=token_id,
            world_id=world_id,
            range_id=range_id,
            target_set=target_set,
            capabilities=capabilities,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        signature = self._mac(self._canonical(fields))
        return RangeOwnershipTokenV1(
            token_id=token_id,
            world_id=world_id,
            range_id=range_id,
            target_set=target_set,
            capabilities=capabilities,
            issued_at=issued_at,
            expires_at=expires_at,
            issuer_signature=signature,
        )

    def verify_token(self, token: RangeOwnershipTokenV1) -> bool:
        """Signature-only check (EXECUTION_POLICY.md §3.2 step 1) — never
        trusts ``token.target_set``'s *contents* for the authorization
        decision (that always comes from the registry); this only confirms
        the token itself was minted by this signer and hasn't been altered.
        """
        fields = self._token_fields(
            token_id=token.token_id,
            world_id=token.world_id,
            range_id=token.range_id,
            target_set=token.target_set,
            capabilities=token.capabilities,
            issued_at=token.issued_at,
            expires_at=token.expires_at,
        )
        expected = self._mac(self._canonical(fields))
        return hmac.compare_digest(expected, token.issuer_signature)

    # -- ExecutionTicketV1 --------------------------------------------------

    def _ticket_fields(
        self, *, ticket_id: Id, request_hash: str, issued_at, expires_at, single_use: bool
    ) -> dict:
        return {
            "ticket_id": str(ticket_id),
            "request_hash": request_hash,
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "single_use": single_use,
        }

    def issue_ticket(self, request_hash: str, *, ttl: timedelta, issued_at=None) -> ExecutionTicketV1:
        """``issued_at`` override exists for the same test-only reason as
        ``mint_token``'s — see its docstring.
        """
        issued_at = issued_at if issued_at is not None else utc_now()
        expires_at = issued_at + ttl
        ticket_id = new_id()
        fields = self._ticket_fields(
            ticket_id=ticket_id,
            request_hash=request_hash,
            issued_at=issued_at,
            expires_at=expires_at,
            single_use=True,
        )
        signature = self._mac(self._canonical(fields))
        return ExecutionTicketV1(
            ticket_id=ticket_id,
            request_hash=request_hash,
            issued_at=issued_at,
            expires_at=expires_at,
            single_use=True,
            signature=signature,
        )

    def verify_ticket(self, ticket: ExecutionTicketV1, *, expected_request_hash: str) -> bool:
        """The executor-side re-check named in EXECUTION_POLICY.md §3.4:
        adversary-adapter/range-runtime/vultr-control call this immediately
        before their side-effecting call, independent of policy-check's own
        ALLOW decision. Checks signature, hash-binding to the exact request,
        and non-expiry. Does NOT enforce single-use itself (that requires
        shared mutable state across executors) — callers that need
        single-use enforcement should additionally consult a ticket-id
        "already consumed" set they own.
        """
        if ticket.request_hash != expected_request_hash:
            return False
        if utc_now() >= ticket.expires_at:
            return False
        fields = self._ticket_fields(
            ticket_id=ticket.ticket_id,
            request_hash=ticket.request_hash,
            issued_at=ticket.issued_at,
            expires_at=ticket.expires_at,
            single_use=ticket.single_use,
        )
        expected = self._mac(self._canonical(fields))
        return hmac.compare_digest(expected, ticket.signature)


__all__ = ["TokenSigner"]
