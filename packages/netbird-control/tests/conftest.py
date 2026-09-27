from __future__ import annotations

import sys
from pathlib import Path

# See packages/vultr-control/tests/conftest.py for the full explanation:
# --import-mode=importlib doesn't auto-add this directory to sys.path, but
# test_client.py does a bare `from fake_netbird_server import ...`.
_THIS_DIR = str(Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
