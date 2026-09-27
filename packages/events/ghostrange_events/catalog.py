"""Peer B / HACP event catalog — re-exports registry for tooling and docs."""

from __future__ import annotations

from ghostrange_events.registry import EVENT_REGISTRY
from ghostrange_events import names as event_names

# UI + API legacy aliases (see docs/ui/EVENTS_CONTRACT.md)
UI_LEGACY_ALIASES = (
    "world.status_changed",
    "compute.worker_upserted",
    "cost.snapshot.updated",
)


def all_event_names() -> list[str]:
    registered = sorted(EVENT_REGISTRY.keys())
    return registered + [a for a in UI_LEGACY_ALIASES if a not in registered]


__all__ = ["EVENT_REGISTRY", "event_names", "UI_LEGACY_ALIASES", "all_event_names"]
