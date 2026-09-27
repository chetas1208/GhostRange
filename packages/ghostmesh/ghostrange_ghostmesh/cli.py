"""CLI for M13 harness demo."""

from __future__ import annotations

import json

from .harness import run_m13_demo_story


def main() -> None:
    result = run_m13_demo_story()
    print(json.dumps(result.__dict__, default=str, indent=2))


if __name__ == "__main__":
    main()
