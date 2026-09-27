"""``StoredEvent``: one durable row from ``event_log``.

Two distinct serializations come off this class, for two different
audiences — do not conflate them:

- ``to_redis_message`` / ``from_redis_message``: the **internal**
  transport shape used only between this package's own
  ``PostgresEventStore``/``RedisBus``/``EventGateway`` (never seen by a
  browser). It nests the pristine event payload under its own ``payload``
  key so it round-trips losslessly through ``typed_payload()`` /
  ``parse_event`` — every ``GhostRangeEvent`` subclass is
  ``extra="forbid"``, so merging storage metadata (``seq``, ``source``, a
  possibly-absent ``range_id``, ...) directly into the payload dict would
  make some event types fail re-validation.
- ``to_client_event``: the **client-facing** WS/SSE wire shape —
  see ``packages/events/README.md`` "Wire contract". This matches what
  ``apps/web``'s already-shipped ``normalizeEnvelope.ts`` /
  ``eventReducer.ts`` actually read (flat object, ``event_name`` as the
  type discriminator, a top-level ``sequence`` field) — confirmed by
  Agent 01's M2 audit as the shape that already won over ADR-011's older
  generic-wrapper sketch. It is a derived, one-way view for output only;
  nothing in this package ever parses a client event back into a
  ``StoredEvent``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from ..registry import parse_event


@dataclass(frozen=True, slots=True)
class StoredEvent:
    """A durably-appended event, exactly as read back from ``event_log``
    (or freshly appended in the same shape). This is the unit both the
    replay query and the live pub-sub tail deal in — the gateway layer
    (``store/gateway.py``) never touches raw psycopg/redis rows directly
    outside this module.
    """

    event_id: uuid.UUID
    range_id: uuid.UUID
    world_id: Optional[uuid.UUID]
    seq: int
    event_type: str
    event_version: str
    occurred_at: datetime
    source: str
    correlation_id: Optional[uuid.UUID]
    payload: dict[str, Any]
    """The pristine ``event.model_dump(mode="json")`` output — never
    mutated with storage metadata, so ``typed_payload()`` always works.
    """

    def typed_payload(self) -> Any:
        """Re-hydrate ``payload`` into its real ``GhostRangeEvent`` subclass
        via the registry, dispatching on the payload's own ``event_name``.
        Raises ``pydantic.ValidationError`` on a corrupt/malformed row, same
        as ``parse_event`` always does — a bad row in the durable log is a
        loud failure, not a silent skip.
        """
        return parse_event(self.payload)

    # -- internal Redis pub-sub transport (never sent to a browser) --------

    def to_redis_message(self) -> dict[str, Any]:
        """Lossless internal representation published to the Range's Redis
        channel. Nests ``payload`` so it stays pristine on the wire.
        """
        return {
            "event_id": str(self.event_id),
            "range_id": str(self.range_id),
            "world_id": str(self.world_id) if self.world_id is not None else None,
            "seq": self.seq,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "occurred_at": self.occurred_at.isoformat(),
            "source": self.source,
            "correlation_id": str(self.correlation_id) if self.correlation_id is not None else None,
            "payload": self.payload,
        }

    @classmethod
    def from_redis_message(cls, data: dict[str, Any]) -> "StoredEvent":
        """Inverse of ``to_redis_message``."""
        occurred_at = data["occurred_at"]
        if isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at)
        return cls(
            event_id=uuid.UUID(str(data["event_id"])),
            range_id=uuid.UUID(str(data["range_id"])),
            world_id=uuid.UUID(str(data["world_id"])) if data.get("world_id") else None,
            seq=int(data["seq"]),
            event_type=data["event_type"],
            event_version=data["event_version"],
            occurred_at=occurred_at,
            source=data["source"],
            correlation_id=(
                uuid.UUID(str(data["correlation_id"])) if data.get("correlation_id") else None
            ),
            payload=data["payload"],
        )

    # -- client-facing WS/SSE wire shape (apps/web-compatible) --------------

    def to_client_event(self) -> dict[str, Any]:
        """The exact JSON object a WS/SSE client receives — flat, no
        ``payload`` wrapper key, ``event_name`` as the type discriminator,
        a top-level ``sequence`` field. Matches
        ``apps/web/src/state/normalizeEnvelope.ts``'s
        ``raw.event_name ?? raw.type`` / ``raw.sequence`` reads exactly.

        This is a derived copy — mutating the returned dict never affects
        ``self.payload``.
        """
        client_event = dict(self.payload)
        client_event["sequence"] = self.seq
        client_event.setdefault("range_id", str(self.range_id))
        if self.world_id is not None:
            client_event.setdefault("world_id", str(self.world_id))
        client_event["source"] = self.source
        if self.correlation_id is not None:
            client_event["correlation_id"] = str(self.correlation_id)
        return client_event


__all__ = ["StoredEvent"]
