"""Persistence round-trip tests: write state, reload (via a *new* store
instance against the same file, simulating a process restart), confirm
identical data. Also checks the append-only/durability properties the
brief calls out explicitly.
"""

from __future__ import annotations

import uuid

from ghostrange_contracts.enums import RangeLifecycleState
from ghostrange_contracts.range import RangeV1

from ghostrange_range_runtime.persistence import SqliteTransitionStore


def test_append_and_history_round_trip(db_path):
    range_id = uuid.uuid4()
    world_id = uuid.uuid4()

    store1 = SqliteTransitionStore(db_path)
    store1.append(
        range_id=range_id,
        world_id=None,
        previous_state=None,
        new_state=RangeLifecycleState.REQUESTED,
        reason="requested",
        correlation_id="c1",
    )
    store1.append(
        range_id=range_id,
        world_id=world_id,
        previous_state=RangeLifecycleState.REQUESTED,
        new_state=RangeLifecycleState.PLANNING,
        reason="validated",
        correlation_id="c2",
    )
    store1.close()

    # Simulate a process restart: brand new store instance, same file.
    store2 = SqliteTransitionStore(db_path)
    history = store2.history(range_id)
    store2.close()

    assert len(history) == 2
    assert history[0].previous_state is None
    assert history[0].new_state == RangeLifecycleState.REQUESTED
    assert history[0].world_id is None
    assert history[1].previous_state == RangeLifecycleState.REQUESTED
    assert history[1].new_state == RangeLifecycleState.PLANNING
    assert history[1].world_id == world_id
    assert history[1].correlation_id == "c2"


def test_latest_state_after_reopen(db_path):
    range_id = uuid.uuid4()
    store1 = SqliteTransitionStore(db_path)
    for prev, new in [
        (None, RangeLifecycleState.REQUESTED),
        (RangeLifecycleState.REQUESTED, RangeLifecycleState.PLANNING),
        (RangeLifecycleState.PLANNING, RangeLifecycleState.PROVISIONING),
    ]:
        store1.append(
            range_id=range_id,
            world_id=None,
            previous_state=prev,
            new_state=new,
            reason="x",
            correlation_id="c",
        )
    store1.close()

    store2 = SqliteTransitionStore(db_path)
    assert store2.latest_state(range_id) == RangeLifecycleState.PROVISIONING
    store2.close()


def test_snapshot_round_trip_is_identical(db_path):
    range_record = RangeV1(spec_id=uuid.uuid4(), status=RangeLifecycleState.PLANNING)
    range_record.root_world_id = uuid.uuid4()
    range_record.world_ids = [range_record.root_world_id]

    store1 = SqliteTransitionStore(db_path)
    store1.save_snapshot(range_record)
    store1.close()

    store2 = SqliteTransitionStore(db_path)
    reloaded = store2.load_snapshot(range_record.id)
    store2.close()

    assert reloaded is not None
    assert reloaded.model_dump() == range_record.model_dump()


def test_snapshot_upsert_keeps_only_latest(db_path):
    range_record = RangeV1(spec_id=uuid.uuid4(), status=RangeLifecycleState.REQUESTED)
    store = SqliteTransitionStore(db_path)
    store.save_snapshot(range_record)

    range_record.status = RangeLifecycleState.PLANNING
    store.save_snapshot(range_record)

    reloaded = store.load_snapshot(range_record.id)
    store.close()

    assert reloaded.status == RangeLifecycleState.PLANNING


def test_missing_snapshot_returns_none(store):
    assert store.load_snapshot(uuid.uuid4()) is None


def test_all_range_ids_reflects_distinct_ranges(db_path):
    r1, r2 = uuid.uuid4(), uuid.uuid4()
    store = SqliteTransitionStore(db_path)
    store.append(
        range_id=r1,
        world_id=None,
        previous_state=None,
        new_state=RangeLifecycleState.REQUESTED,
        reason="x",
        correlation_id="c",
    )
    store.append(
        range_id=r2,
        world_id=None,
        previous_state=None,
        new_state=RangeLifecycleState.REQUESTED,
        reason="x",
        correlation_id="c",
    )
    ids = set(store.all_range_ids())
    store.close()
    assert ids == {r1, r2}


def test_rebuild_range_state_matches_latest_state(db_path):
    range_id = uuid.uuid4()
    store = SqliteTransitionStore(db_path)
    for prev, new in [
        (None, RangeLifecycleState.REQUESTED),
        (RangeLifecycleState.REQUESTED, RangeLifecycleState.PLANNING),
    ]:
        store.append(
            range_id=range_id,
            world_id=None,
            previous_state=prev,
            new_state=new,
            reason="x",
            correlation_id="c",
        )
    rebuilt = store.rebuild_range_state(range_id)
    latest = store.latest_state(range_id)
    store.close()
    assert rebuilt == latest == RangeLifecycleState.PLANNING


def test_rebuild_range_state_for_unknown_range_is_none(store):
    assert store.rebuild_range_state(uuid.uuid4()) is None
