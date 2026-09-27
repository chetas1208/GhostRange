"""Tests for the event persistence layer (append -> publish -> persist ->
replay, and replay + live-handoff), run against a REAL Postgres + Redis/
Valkey (see conftest.py / docker-compose.dev.yml at the repo root).

Scope, explicitly:
- Ordering guarantees (seq is per-range monotonic, assigned race-free under
  concurrent appends).
- Replay correctness (since_seq semantics, full round trip through the
  actual append/publish/persist/replay path — not just serialization,
  which M1's packages/events/tests/test_roundtrip.py already covers).
- Replay + live-handoff with no gap and no duplicate (the specific test
  the M2 brief asks for).
- Reconnect-after-gap behavior, both the "self-heals mid-stream" case and
  the literal "client disconnects, reconnects with since_seq" case.

Every test here is skipped (with a stated reason, not silently passed) if
Postgres/Redis aren't reachable — see conftest.py's requires_store_infra.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import asynccontextmanager

import psycopg
import pytest

from ghostrange_events.store import RedisBus
from ghostrange_events.store.gateway import EventGateway
from ghostrange_events.world_events import WorldProvisioningV1

# Skipped (with a stated reason, not silently passed) if Postgres/Redis
# aren't reachable. Duplicated (not imported) from conftest.py's
# _infra_reachable check because pytest test modules aren't a Python
# package here (no __init__.py, matching the rest of packages/events/tests)
# so a relative `from .conftest import ...` doesn't resolve.
try:
    _dsn = os.environ.get("POSTGRES_DSN", "postgresql://ghostrange:ghostrange@localhost:5432/ghostrange")
    _conn = psycopg.connect(_dsn, connect_timeout=3)
    _conn.execute("SELECT 1")
    _conn.close()
    import redis as _redis_sync

    _redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    _client = _redis_sync.Redis.from_url(_redis_url, socket_connect_timeout=3)
    _client.ping()
    _client.close()
    _SKIP_REASON = ""
except Exception as _exc:  # noqa: BLE001
    _SKIP_REASON = f"store infra unreachable: {_exc}"

pytestmark = pytest.mark.skipif(bool(_SKIP_REASON), reason=_SKIP_REASON)


def _make_event(range_id: uuid.UUID) -> WorldProvisioningV1:
    return WorldProvisioningV1(world_id=uuid.uuid4(), range_id=range_id)


# ---------------------------------------------------------------------------
# Ordering + full round trip
# ---------------------------------------------------------------------------


async def test_seq_is_monotonic_per_range_starting_at_1(gateway, range_id):
    events = [_make_event(range_id) for _ in range(4)]
    stored = [await gateway.append_and_publish(range_id, e, source="test") for e in events]
    assert [s.seq for s in stored] == [1, 2, 3, 4]


async def test_seq_assignment_is_race_free_under_concurrent_appends(gateway, range_id):
    """Directly exercises the concern ADR-011 flags: a naive
    ``SELECT MAX(seq)+1`` read-then-write races under concurrent appends to
    the *same* range. Fire 25 concurrent appends and assert the resulting
    seqs are exactly {1..25} — no duplicate, no gap, regardless of
    completion order.
    """
    n = 25
    events = [_make_event(range_id) for _ in range(n)]
    stored = await asyncio.gather(
        *[gateway.append_and_publish(range_id, e, source="test") for e in events]
    )
    seqs = sorted(s.seq for s in stored)
    assert seqs == list(range(1, n + 1))


async def test_seq_counters_are_independent_across_ranges(gateway, range_id):
    other_range_id = uuid.uuid4()
    a = await gateway.append_and_publish(range_id, _make_event(range_id), source="test")
    b = await gateway.append_and_publish(other_range_id, _make_event(other_range_id), source="test")
    assert a.seq == 1
    assert b.seq == 1  # independent counters, not a shared global sequence


async def test_full_append_publish_persist_replay_round_trip(gateway, range_id):
    """Not just JSON serialization (M1 already covers that) — the actual
    event object survives append() -> Postgres -> replay() -> a
    freshly-constructed StoredEvent -> typed_payload(), and comes back
    equal to the object that was appended.
    """
    original = _make_event(range_id)
    stored_at_append = await gateway.append_and_publish(range_id, original, source="range-runtime")

    replayed = await gateway.store.replay(range_id, since_seq=0)
    assert len(replayed) == 1
    row = replayed[0]

    assert row.event_id == original.event_id
    assert row.seq == stored_at_append.seq
    assert row.source == "range-runtime"
    assert row.typed_payload() == original

    # Client-facing wire shape: flat, event_name-keyed, top-level sequence
    # — matches apps/web's normalizeEnvelope.ts, not a nested envelope.
    wire = row.to_client_event()
    assert wire["event_name"] == "world.provisioning"
    assert wire["sequence"] == stored_at_append.seq
    assert "payload" not in wire  # flat, no wrapper key
    assert wire["world_id"] == str(original.world_id)


async def test_replay_since_seq_excludes_already_seen_events(gateway, range_id):
    events = [_make_event(range_id) for _ in range(5)]
    for e in events:
        await gateway.append_and_publish(range_id, e, source="test")

    all_events = await gateway.store.replay(range_id, since_seq=0)
    assert [e.seq for e in all_events] == [1, 2, 3, 4, 5]

    tail_only = await gateway.store.replay(range_id, since_seq=3)
    assert [e.seq for e in tail_only] == [4, 5]

    nothing_new = await gateway.store.replay(range_id, since_seq=5)
    assert nothing_new == []


# ---------------------------------------------------------------------------
# Replay + live handoff: no gap, no duplicate
# ---------------------------------------------------------------------------


async def test_replay_then_live_handoff_no_gap_no_duplicate(gateway, range_id):
    """The specific scenario the M2 brief asks for: publish some events,
    connect (replay), publish more events *concurrently* while the client
    is already streaming, and assert the client sees exactly the right
    set, in order, with no gaps and no duplicates.
    """
    initial_events = [_make_event(range_id) for _ in range(3)]
    for e in initial_events:
        await gateway.append_and_publish(range_id, e, source="test")

    stream = gateway.stream(range_id, since_seq=0)
    seen = []
    try:
        # Drain exactly the replay batch first. Receiving all 3 here proves
        # subscribe() + the replay query both already completed — only
        # after this do we start concurrent live producers.
        for _ in range(3):
            seen.append(await asyncio.wait_for(stream.__anext__(), timeout=5))
        assert [s.seq for s in seen] == [1, 2, 3]

        live_events = [_make_event(range_id) for _ in range(12)]

        async def produce():
            for e in live_events:
                await gateway.append_and_publish(range_id, e, source="test")
                await asyncio.sleep(0.01)  # interleave with the consumer

        producer_task = asyncio.create_task(produce())
        try:
            for _ in range(len(live_events)):
                seen.append(await asyncio.wait_for(stream.__anext__(), timeout=5))
        finally:
            await producer_task
    finally:
        await stream.aclose()

    seqs = [s.seq for s in seen]
    assert seqs == list(range(1, 16)), "must be strictly ascending, no gap"
    assert len(seqs) == len(set(seqs)), "no duplicate seq delivered"

    expected_event_ids = [e.event_id for e in initial_events + live_events]
    actual_event_ids = [s.event_id for s in seen]
    assert actual_event_ids == expected_event_ids, "must be exactly the right set, in order"


async def test_reconnect_with_since_seq_resumes_without_gap_or_duplicate(gateway, range_id):
    """Literal reconnect: a client disconnects mid-stream and reconnects
    with since_seq=last_applied_seq. The two connections' deliveries,
    concatenated, must be exactly the full set once each, in order.
    """
    events = [_make_event(range_id) for _ in range(5)]
    for e in events:
        await gateway.append_and_publish(range_id, e, source="test")

    stream1 = gateway.stream(range_id, since_seq=0)
    first_batch = []
    try:
        for _ in range(3):
            first_batch.append(await asyncio.wait_for(stream1.__anext__(), timeout=5))
    finally:
        await stream1.aclose()  # simulate the WS connection dropping

    last_applied_seq = first_batch[-1].seq
    assert last_applied_seq == 3

    stream2 = gateway.stream(range_id, since_seq=last_applied_seq)
    second_batch = []
    try:
        for _ in range(2):
            second_batch.append(await asyncio.wait_for(stream2.__anext__(), timeout=5))
    finally:
        await stream2.aclose()

    all_seen = first_batch + second_batch
    assert [s.seq for s in all_seen] == [1, 2, 3, 4, 5]
    assert len({s.event_id for s in all_seen}) == 5


# ---------------------------------------------------------------------------
# Gap-heal on the live side (simulated dropped pub-sub delivery)
# ---------------------------------------------------------------------------


class _FilteredSubscription:
    """Wraps a real LiveSubscription, silently swallowing messages whose
    seq is in ``drop_seqs`` — simulating Redis/Valkey actually losing a
    published message in transit (pub-sub has no delivery guarantee; this
    can genuinely happen, e.g. a brief network hiccup on the subscriber's
    connection). Used to prove EventGateway.stream()'s gap-heal path
    (re-querying Postgres) recovers correctly, rather than the seq check
    only ever being exercised by the "arrived twice" direction.
    """

    def __init__(self, inner, drop_seqs: set[int]) -> None:
        self._inner = inner
        self._drop_seqs = drop_seqs

    async def __aiter__(self):
        async for event in self._inner:
            if event.seq in self._drop_seqs:
                continue
            yield event


class _DropSeqBus:
    def __init__(self, inner: RedisBus, drop_seqs: set[int]) -> None:
        self._inner = inner
        self._drop_seqs = drop_seqs

    async def publish(self, stored_event) -> None:
        await self._inner.publish(stored_event)

    @asynccontextmanager
    async def subscribe(self, range_id: uuid.UUID):
        async with self._inner.subscribe(range_id) as live:
            yield _FilteredSubscription(live, self._drop_seqs)


async def test_gap_on_live_tail_is_healed_from_postgres_without_reconnect(
    pg_store, redis_bus, range_id
):
    producer_gateway = EventGateway(pg_store, redis_bus)
    consumer_gateway = EventGateway(pg_store, _DropSeqBus(redis_bus, drop_seqs={2}))

    seed = _make_event(range_id)
    seed_stored = await producer_gateway.append_and_publish(range_id, seed, source="test")
    assert seed_stored.seq == 1

    stream = consumer_gateway.stream(range_id, since_seq=0)
    try:
        first = await asyncio.wait_for(stream.__anext__(), timeout=5)
        assert first.seq == 1  # replay batch — subscribe+replay already ran

        ev2 = _make_event(range_id)
        ev3 = _make_event(range_id)
        # seq=2's live delivery is dropped by the filter (simulated loss);
        # seq=3 arrives live looking like a gap (skipped from 1 -> 3).
        await producer_gateway.append_and_publish(range_id, ev2, source="test")
        await producer_gateway.append_and_publish(range_id, ev3, source="test")

        second = await asyncio.wait_for(stream.__anext__(), timeout=5)
        third = await asyncio.wait_for(stream.__anext__(), timeout=5)
    finally:
        await stream.aclose()

    # seq=2 was never delivered live, yet the consumer still saw it, healed
    # from the durable log — and in the correct order relative to seq=3.
    assert (second.seq, second.event_id) == (2, ev2.event_id)
    assert (third.seq, third.event_id) == (3, ev3.event_id)


async def test_publish_failure_does_not_prevent_durable_append(pg_store, range_id):
    """ADR-011 §1: append precedes publish, and publish is best-effort —
    a producer must never fail to make durable progress just because Redis
    is unreachable. Point the gateway at a bus whose publish always raises.
    """

    class _BrokenBus:
        async def publish(self, stored_event) -> None:
            raise ConnectionError("simulated Redis outage")

    gateway = EventGateway(pg_store, _BrokenBus())
    event = _make_event(range_id)

    stored = await gateway.append_and_publish(range_id, event, source="test")
    assert stored.seq == 1

    replayed = await pg_store.replay(range_id, since_seq=0)
    assert len(replayed) == 1
    assert replayed[0].event_id == event.event_id
