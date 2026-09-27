from __future__ import annotations

import sys
from pathlib import Path

# --import-mode=importlib (pytest.ini) does not auto-add this directory to
# sys.path the way the classic import mode did. Sibling test files here do
# bare imports (`from conftest import make_compute_req`, `from
# fake_vultr_server import FakeVultrServer`) rather than package-relative
# ones. pytest always loads a directory's own conftest.py by absolute file
# path regardless of import mode, so inserting the path here (before any
# sibling test file is collected) restores that convention safely.
_THIS_DIR = str(Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import pytest

from ghostrange_vultr_control import CreateWorldRequest, GhostRangeTags


@pytest.fixture
def tags() -> GhostRangeTags:
    return GhostRangeTags(range_id="range-1", world_id="world-1")


@pytest.fixture
def world_req(tags: GhostRangeTags) -> CreateWorldRequest:
    return CreateWorldRequest(region="ewr", tags=tags)


