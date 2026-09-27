"""Hash-chained event log for tamper-evident sequencing."""

from __future__ import annotations

import hashlib
from typing import Any

from ghostrange_contracts.ghostledger_m7 import EventCheckpointV1

from .canonical import canonical_json_bytes


GENESIS = "sha256:" + "0" * 64


def hash_event(event: dict[str, Any], previous_hash: str) -> str:
    payload = {"previous": previous_hash, "event": event}
    h = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return f"sha256:{h}"


def chain_events(events: list[dict]) -> tuple[list[dict], str]:
    prev = GENESIS
    chained: list[dict] = []
    for ev in events:
        eh = hash_event(ev, prev)
        chained.append({**ev, "previous_event_hash": prev, "event_hash": eh})
        prev = eh
    return chained, prev


def verify_event_chain(chained: list[dict]) -> bool:
    prev = GENESIS
    for ev in chained:
        if ev.get("previous_event_hash") != prev:
            return False
        base = {k: v for k, v in ev.items() if k not in ("previous_event_hash", "event_hash")}
        expected = hash_event(base, prev)
        if ev.get("event_hash") != expected:
            return False
        prev = ev["event_hash"]
    return True


def checkpoint(sequence: int, latest_hash: str, experiment_run_id) -> EventCheckpointV1:
    body = {"sequence": sequence, "latest": latest_hash, "run": str(experiment_run_id)}
    d = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return EventCheckpointV1(
        sequence=sequence,
        latest_event_hash=latest_hash,
        experiment_run_id=experiment_run_id,
        checkpoint_digest=f"sha256:{d}",
    )


__all__ = ["chain_events", "verify_event_chain", "checkpoint", "GENESIS"]
