from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RANGE_DIR = REPO_ROOT / "ranges" / "ghostrange-auth-lab-v1"


@pytest.fixture()
def range_dir() -> Path:
    assert RANGE_DIR.is_dir(), f"expected canonical range dir at {RANGE_DIR}"
    return RANGE_DIR
