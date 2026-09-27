"""Orphan reconciliation CLI — only ever acts on resources GhostRange itself
tagged as owned (via ``ShieldedComputeProvider`` / ``GhostRangeTags``).

Delegates the actual find/terminate logic to ``orphan_reaper`` so this CLI
and the scheduled in-process sweep (``main.py``'s lifespan) and the manual
admin endpoint (``scheduler_routes.py``'s ``POST /v1/scheduler/reap-orphans``)
all share one implementation and one safety policy — there is exactly one
place that decides what counts as an orphan.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compute_provider import build_compute_provider
from .config import Settings
from .orphan_reaper import reap_orphans


def cli() -> None:
    parser = argparse.ArgumentParser(description="GhostRange provider reconciliation")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="Actually terminate owned TTL-expired orphans")
    args = parser.parse_args()
    dry_run = not args.apply

    settings = Settings.from_env()
    provider = build_compute_provider(settings)

    owned_resources = [
        {
            "provider": h.provider,
            "provider_compute_id": h.provider_compute_id,
            "world_ref": h.world_ref,
            "region": h.region,
            "plan": h.plan,
            "created_at": h.created_at.isoformat(),
            "ttl_seconds": h.ttl_seconds,
        }
        for h in provider.list_all_ghostrange_workers()
    ]

    reap_report = reap_orphans(provider, dry_run=dry_run)

    report = {
        "dry_run": dry_run,
        "checked_at": reap_report["checked_at"],
        "owned_resources": owned_resources,
        "orphans": reap_report["orphans_found"],
        "terminated": reap_report["terminated"],
        "would_terminate": reap_report["would_terminate"],
        "failed": reap_report["failed"],
        "still_present_after_reap": reap_report["still_present_after_reap"],
    }
    out = Path("artifacts/reconcile-report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    cli()
