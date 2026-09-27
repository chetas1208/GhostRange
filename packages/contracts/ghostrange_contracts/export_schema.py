"""Export JSON Schema for every contract model to packages/contracts/schemas/.

Usage::

    python -m ghostrange_contracts.export_schema [output_dir]

``output_dir`` defaults to ``<repo>/packages/contracts/schemas``. This is
the artifact CI checks the hand-written frontend TypeScript types against
(per Decisions.md #3: no runtime codegen yet in M1, but the JSON Schema is
the ground truth those hand-written types must not drift from).
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel

import ghostrange_contracts as contracts

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "schemas"


def _iter_model_classes() -> Iterator[type[BaseModel]]:
    """Yield every pydantic model class publicly exported by the package."""
    seen: set[type[BaseModel]] = set()
    for name in contracts.__all__:
        obj = getattr(contracts, name)
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj not in seen:
            seen.add(obj)
            yield obj


def export_all(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    """Write one <ClassName>.json JSON Schema file per model. Returns the
    list of paths written. Raises on any model that fails to export —
    schema export failures must not be silently skipped.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for model_cls in _iter_model_classes():
        schema = model_cls.model_json_schema()
        out_path = output_dir / f"{model_cls.__name__}.json"
        out_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
        written.append(out_path)
    return written


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    output_dir = Path(argv[0]) if argv else DEFAULT_OUTPUT_DIR
    written = export_all(output_dir)
    for path in written:
        print(f"wrote {path}")
    print(f"exported {len(written)} schemas to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
