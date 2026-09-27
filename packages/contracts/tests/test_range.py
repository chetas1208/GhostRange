from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from ghostrange_contracts.enums import AssetRole, RangeLifecycleState
from ghostrange_contracts.range import (
    AssetSpecV1,
    NetworkSpecV1,
    RangeSpecV1,
    RangeV1,
    assert_transition,
    can_transition,
)


def _make_network() -> NetworkSpecV1:
    return NetworkSpecV1(name="corp-lan", cidr="10.0.0.0/24")


def test_valid_range_spec_constructs():
    net = _make_network()
    asset = AssetSpecV1(
        hostname="dc01",
        network_id=net.id,
        os_family="windows",
        role=AssetRole.DOMAIN_CONTROLLER,
        image="win2019-base",
    )
    spec = RangeSpecV1(
        name="incident-42-repro",
        owner="chetasparekh2003@gmail.com",
        networks=[net],
        assets=[asset],
    )
    assert spec.schema_version == "1"
    assert spec.assets[0].role == AssetRole.DOMAIN_CONTROLLER
    assert spec.networks[0].cidr == "10.0.0.0/24"


def test_range_spec_rejects_unknown_field():
    with pytest.raises(ValidationError):
        RangeSpecV1(
            name="bad",
            owner="a@b.com",
            not_a_real_field="surprise",
        )


def test_range_spec_requires_owner():
    with pytest.raises(ValidationError):
        RangeSpecV1(name="no-owner")


def test_asset_spec_rejects_invalid_role():
    net = _make_network()
    with pytest.raises(ValidationError):
        AssetSpecV1(
            hostname="dc01",
            network_id=net.id,
            os_family="windows",
            role="NOT_A_REAL_ROLE",
            image="win2019-base",
        )


def test_range_v1_defaults_to_requested():
    r = RangeV1(spec_id=_make_network().id)
    assert r.status == RangeLifecycleState.REQUESTED
    assert r.world_ids == []


@pytest.mark.parametrize(
    "current,target,expected",
    [
        (RangeLifecycleState.REQUESTED, RangeLifecycleState.PLANNING, True),
        (RangeLifecycleState.REQUESTED, RangeLifecycleState.READY, False),
        (RangeLifecycleState.READY, RangeLifecycleState.EXECUTING, True),
        (RangeLifecycleState.READY, RangeLifecycleState.FAILED, True),
        (RangeLifecycleState.EXECUTING, RangeLifecycleState.VERIFYING, True),
        (RangeLifecycleState.VERIFYING, RangeLifecycleState.EXECUTING, True),
        (RangeLifecycleState.DESTROYED, RangeLifecycleState.READY, False),
        (RangeLifecycleState.FAILED, RangeLifecycleState.PLANNING, False),
        (RangeLifecycleState.STOPPING, RangeLifecycleState.DESTROYING, True),
    ],
)
def test_lifecycle_transitions(current, target, expected):
    assert can_transition(current, target) is expected


def test_assert_transition_raises_on_illegal_move():
    with pytest.raises(ValueError):
        assert_transition(RangeLifecycleState.DESTROYED, RangeLifecycleState.READY)


def test_assert_transition_passes_on_legal_move():
    assert_transition(RangeLifecycleState.REQUESTED, RangeLifecycleState.PLANNING)


def test_failed_is_terminal_and_reachable_from_every_nonterminal_state():
    from ghostrange_contracts.range import RANGE_LIFECYCLE_TRANSITIONS, TERMINAL_RANGE_STATES

    for state in RangeLifecycleState:
        if state in TERMINAL_RANGE_STATES:
            assert RANGE_LIFECYCLE_TRANSITIONS[state] == frozenset()
        else:
            assert RangeLifecycleState.FAILED in RANGE_LIFECYCLE_TRANSITIONS[state]
