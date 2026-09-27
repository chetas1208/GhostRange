"""Orphan reconciliation — only delete resources tagged as GhostRange-owned."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cli() -> None:
    parser = argparse.ArgumentParser(description="GhostRange provider reconciliation")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="Actually delete owned orphans")
    args = parser.parse_args()
    dry_run = not args.apply
    report = {
        "dry_run": dry_run,
        "owned_resources": [],
        "orphans": [],
        "note": "M2: wire to vultr-control list-by-tag when LIVE_PROVIDER=vultr",
    }
    out = Path("artifacts/reconcile-report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    cli()
