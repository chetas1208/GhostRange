from __future__ import annotations

import pytest

from ghostrange_vultr_control import CreateComputeRequest, CreateWorldRequest, GhostRangeTags


@pytest.fixture
def tags() -> GhostRangeTags:
    return GhostRangeTags(range_id="range-1", world_id="world-1")


@pytest.fixture
def world_req(tags: GhostRangeTags) -> CreateWorldRequest:
    return CreateWorldRequest(region="ewr", tags=tags)


def make_compute_req(world_ref: str, tags: GhostRangeTags, **overrides) -> CreateComputeRequest:
    defaults = dict(
        world_ref=world_ref,
        region="ewr",
        plan="vc2-1c-1gb",
        tags=tags,
        os_id=387,
    )
    defaults.update(overrides)
    return CreateComputeRequest(**defaults)
