"""Private evaluator storage — not for production runtime imports."""

from __future__ import annotations

import json
from pathlib import Path

from ghostrange_contracts.ghostarena_m19 import ArenaHiddenBundleV1

DEFAULT_PRIVATE_ROOT = Path(__file__).resolve().parents[3] / "evaluation" / "private"


class ArenaHiddenStore:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or DEFAULT_PRIVATE_ROOT
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, bundle: ArenaHiddenBundleV1) -> None:
        path = self._root / f"{bundle.scenario_id}.json"
        path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")

    def get(self, scenario_id: str) -> ArenaHiddenBundleV1 | None:
        path = self._root / f"{scenario_id}.json"
        if not path.exists():
            return None
        return ArenaHiddenBundleV1.model_validate_json(path.read_text(encoding="utf-8"))

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self._root.glob("*.json"))
