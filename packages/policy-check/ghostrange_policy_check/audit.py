"""Append-only, hash-chained audit log (EXECUTION_POLICY.md §8).

M2 stub: in-memory list, process-local. Production storage is Postgres
with an application DB role granted INSERT/SELECT only (no UPDATE/DELETE) —
a deployment-layer control this stub cannot itself provide, but the shape
it produces (each record's ``prev_hash`` chaining to the previous record's
own hash) is the same shape that storage-layer control protects, and
``verify_chain()`` below is the same check a detection job would run
against the real table.

Every ``authorize()`` call — ALLOW or DENY — produces exactly one record
here (EXECUTION_POLICY.md: "denials are signal, not noise"). Nothing about
this module reads or forwards request ``params`` or any credential-shaped
field into the record; ``AuditRecordV1``'s shape has no field for that by
construction (see policy.py), so there is nothing here for a secret to
leak through even before ``secrets.redact_secrets`` would apply.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from typing import Literal, Optional

from ghostrange_contracts._base import Id, utc_now
from ghostrange_contracts.enums import PolicyDenyReason
from ghostrange_contracts.policy import ActorRef, AuditRecordV1, ProvenanceRef, TargetRef

GENESIS_HASH = "0" * 64


class AuditLog:
    """One hash-chained sequence of ``AuditRecordV1``. Thread-safe via a
    single lock (append is the only mutation).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[AuditRecordV1] = []

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records)

    @property
    def records(self) -> list[AuditRecordV1]:
        return list(self._records)

    def _record_hash(self, *, seq: int, prev_hash: str, payload: dict) -> str:
        canonical = json.dumps(
            {"seq": seq, "prev_hash": prev_hash, **payload}, sort_keys=True, default=str
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def append(
        self,
        *,
        actor: ActorRef,
        request_hash: str,
        decision: Literal["ALLOW", "DENY"],
        reason: Optional[PolicyDenyReason],
        world_id: Id,
        range_id: Optional[Id],
        target_refs: list[TargetRef],
        provenance: ProvenanceRef,
        signing_key: bytes,
    ) -> AuditRecordV1:
        with self._lock:
            seq = len(self._records)
            prev_hash = self._records[-1].signature if self._records else GENESIS_HASH
            timestamp = utc_now()
            payload = {
                "timestamp": timestamp.isoformat(),
                "actor": actor.model_dump(mode="json"),
                "request_hash": request_hash,
                "decision": decision,
                "reason": reason.value if reason is not None else None,
                "world_id": str(world_id),
                "range_id": str(range_id) if range_id is not None else None,
                "target_refs": [t.model_dump(mode="json") for t in target_refs],
                "provenance": provenance.model_dump(mode="json"),
            }
            record_hash = self._record_hash(seq=seq, prev_hash=prev_hash, payload=payload)
            signature = hmac.new(
                signing_key, record_hash.encode("utf-8"), hashlib.sha256
            ).hexdigest()
            record = AuditRecordV1(
                seq=seq,
                prev_hash=prev_hash,
                timestamp=timestamp,
                actor=actor,
                request_hash=request_hash,
                decision=decision,
                reason=reason,
                world_id=world_id,
                range_id=range_id,
                target_refs=target_refs,
                provenance=provenance,
                signature=signature,
            )
            self._records.append(record)
            return record

    def verify_chain(self) -> bool:
        """Independent-of-signing-key structural check: every record's
        ``prev_hash`` must equal the previous record's ``signature``. A
        break here means the log was tampered with or reordered.
        """
        prev = GENESIS_HASH
        for record in self._records:
            if record.prev_hash != prev:
                return False
            prev = record.signature
        return True


__all__ = ["AuditLog", "GENESIS_HASH"]
