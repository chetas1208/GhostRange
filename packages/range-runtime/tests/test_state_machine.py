"""Exhaustive coverage of the Range lifecycle as driven through the
engine (not just the bare contracts function, which packages/contracts'
own test suite already covers): every legal transition in
``RANGE_LIFECYCLE_TRANSITIONS`` must succeed *and* be durably persisted
and published through the engine; every other (current, target) pair
must raise and leave no trace.
"""

from __future__ import annotations

import itertools

import pytest
from ghostrange_contracts.enums import RangeLifecycleState
from ghostrange_contracts.range import RANGE_LIFECYCLE_TRANSITIONS, RangeV1

from ghostrange_range_runtime.errors import IllegalTransitionError
from ghostrange_range_runtime.events import RangeTransitionEventV1

ALL_STATES = list(RangeLifecycleState)

LEGAL_PAIRS = [
    (current, target)
    for current, targets in RANGE_LIFECYCLE_TRANSITIONS.items()
    for target in targets
]

ILLEGAL_PAIRS = [
    (current, target)
    for current, target in itertools.product(ALL_STATES, ALL_STATES)
    if target not in RANGE_LIFECYCLE_TRANSITIONS.get(current, frozenset())
]


def _bare_range(status: RangeLifecycleState) -> RangeV1:
    import uuid

    r = RangeV1(spec_id=uuid.uuid4(), status=RangeLifecycleState.REQUESTED)
    r.status = status
    r.root_world_id = uuid.uuid4()
    return r


@pytest.mark.parametrize("current,target", LEGAL_PAIRS)
def test_every_legal_transition_succeeds(engine, store, sink, current, target):
    range_record = _bare_range(current)
    before_count = len(store.history(range_record.id))

    result = engine._transition(range_record, target, reason="test", correlation_id="corr-1")

    assert result.status == target
    history = store.history(range_record.id)
    assert len(history) == before_count + 1
    assert history[-1].previous_state == current
    assert history[-1].new_state == target
    assert history[-1].correlation_id == "corr-1"
    # exactly one RangeTransitionEventV1 published for this hop
    range_events = [e for e in sink.events if isinstance(e, RangeTransitionEventV1)]
    assert range_events[-1].previous_state == current
    assert range_events[-1].new_state == target


@pytest.mark.parametrize("current,target", ILLEGAL_PAIRS)
def test_every_illegal_transition_raises_and_persists_nothing(engine, store, sink, current, target):
    range_record = _bare_range(current)
    before_count = len(store.history(range_record.id))
    before_events = len(sink.events)

    with pytest.raises(ValueError):
        engine._transition(range_record, target, reason="should not happen", correlation_id="corr-2")

    # raised as the richer type too
    with pytest.raises(IllegalTransitionError):
        engine._transition(range_record, target, reason="should not happen", correlation_id="corr-2")

    assert range_record.status == current, "status must not change on an illegal transition"
    assert len(store.history(range_record.id)) == before_count, "illegal transition must not be persisted"
    assert len(sink.events) == before_events, "illegal transition must not publish an event"


def test_failed_is_reachable_from_every_non_terminal_state(engine):
    for state in ALL_STATES:
        if state in (RangeLifecycleState.DESTROYED, RangeLifecycleState.FAILED):
            continue
        range_record = _bare_range(state)
        result = engine._transition(
            range_record, RangeLifecycleState.FAILED, reason="forced", correlation_id="corr-3"
        )
        assert result.status == RangeLifecycleState.FAILED
        assert result.failure_reason == "forced"


def test_terminal_states_have_no_legal_outgoing_transitions():
    assert RANGE_LIFECYCLE_TRANSITIONS[RangeLifecycleState.DESTROYED] == frozenset()
    assert RANGE_LIFECYCLE_TRANSITIONS[RangeLifecycleState.FAILED] == frozenset()


def test_requested_to_ready_directly_is_illegal(engine):
    range_record = _bare_range(RangeLifecycleState.REQUESTED)
    with pytest.raises(IllegalTransitionError):
        engine._transition(
            range_record, RangeLifecycleState.READY, reason="skip ahead", correlation_id="corr-4"
        )


def test_ready_to_provisioning_without_recovery_semantics_is_illegal(engine):
    range_record = _bare_range(RangeLifecycleState.READY)
    with pytest.raises(IllegalTransitionError):
        engine._transition(
            range_record,
            RangeLifecycleState.PROVISIONING,
            reason="go backwards",
            correlation_id="corr-5",
        )
