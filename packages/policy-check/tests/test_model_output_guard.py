from __future__ import annotations

import uuid

import pytest
from ghostrange_contracts.policy import TargetRef

from ghostrange_policy_check import PolicyRegistry, UnknownTargetAliasError, resolve_target


def test_resolve_target_via_declared_alias():
    registry = PolicyRegistry()
    range_id = uuid.uuid4()
    target = TargetRef(range_id=range_id, host_or_ip="10.20.0.5")
    registry.register_range(range_id, [target], target_aliases={"web-server": target})

    resolved = resolve_target(range_id, "web-server", registry)
    assert resolved == target


def test_resolve_target_rejects_a_raw_ip_the_model_invented():
    """The core property: even a perfectly plausible-looking raw IP/host
    string emitted by the model is never accepted as an alias -- it must
    always be one of the pre-declared alias strings, never free text.
    """
    registry = PolicyRegistry()
    range_id = uuid.uuid4()
    target = TargetRef(range_id=range_id, host_or_ip="10.20.0.5")
    registry.register_range(range_id, [target], target_aliases={"web-server": target})

    with pytest.raises(UnknownTargetAliasError):
        # the model "helpfully" just typed the real IP instead of the alias
        resolve_target(range_id, "10.20.0.5", registry)


def test_resolve_target_rejects_alias_from_wrong_range():
    registry = PolicyRegistry()
    range_a = uuid.uuid4()
    range_b = uuid.uuid4()
    target_a = TargetRef(range_id=range_a, host_or_ip="10.20.0.5")
    registry.register_range(range_a, [target_a], target_aliases={"web-server": target_a})

    with pytest.raises(UnknownTargetAliasError):
        resolve_target(range_b, "web-server", registry)


def test_resolve_target_on_unprovisioned_range_raises():
    registry = PolicyRegistry()
    with pytest.raises(UnknownTargetAliasError):
        resolve_target(uuid.uuid4(), "anything", registry)
