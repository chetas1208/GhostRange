"""Durable event log + live pub-sub, implementing ADR-011's design end to
end: append-then-publish on the write side, replay-then-live-tail (no gap,
no duplicate) on the read side.

Requires the ``store`` extra: ``pip install -e "packages/events[store]"``.
Everything else in ``ghostrange_events`` (the event schemas/registry) has
no such requirement — this subpackage is the only part that needs a real
Postgres/Redis to run against.
"""

from .gateway import EventGateway
from .models import StoredEvent
from .postgres import PostgresEventStore, SeqAssignmentError
from .pubsub import RedisBus, channel_name

__all__ = [
    "EventGateway",
    "StoredEvent",
    "PostgresEventStore",
    "SeqAssignmentError",
    "RedisBus",
    "channel_name",
]
