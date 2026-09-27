"""Shared helper builders for vultr-control's tests.

Kept out of conftest.py deliberately: multiple packages' test suites have
their own conftest.py that other test files bare-import from (`from conftest
import ...`), which is only safe when that package's tests are never
collected in the same pytest run as another package doing the same thing.
Uniquely-named helper modules like this one avoid that collision entirely.
"""
from __future__ import annotations

from ghostrange_vultr_control import CreateComputeRequest, GhostRangeTags


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
