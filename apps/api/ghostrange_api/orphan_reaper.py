"""General-purpose TTL orphan reaper for GhostRange-owned Vultr Compute VMs.

Why this exists
----------------
``GhostRangeTags.ttl_seconds`` (see ``ghostrange_vultr_control.models``) has
always been designed as the mechanism for detecting a worker VM that has
outlived its intended lifetime — the class docstring there literally says
"an orphan-reaper job compares created_at + ttl_seconds to now" — but no
such job existed until this module. This is the general-purpose safety net:
it does not care *why* a worker never got torn down (crashed orchestrator,
killed process, a code path that forgot to call ``terminate_worker``, a
manual test that never cleaned up, ...) — it only cares that a resource
GhostRange created has now outlived the TTL it was tagged with at creation
time, and that costs real money every hour it keeps running.

This only works because ``ComputeRecord.created_at`` is now populated from
Vultr's real ``date_created`` field (see
``ghostrange_vultr_control.real_provider._parse_vultr_datetime`` /
``_compute_record_from_api``) instead of always defaulting to "now" — that
fix is what makes a TTL comparison against ``created_at`` meaningful instead
of vacuously false forever.

The no-TTL judgment call
------------------------
A ``WorkerHandle`` with ``ttl_seconds is None`` is NEVER auto-reaped by this
module, no matter how old ``created_at`` is. This is a deliberate policy
decision, not an oversight:

- ``ttl_seconds`` is an *advisory* field on ``GhostRangeTags`` — it can be
  absent on a resource that predates this field, was created by some other
  tool/manual `govultr`/`vultr-cli` call that stamped GhostRange's tag
  prefix without the ttl suffix, or was intentionally created without an
  expiry (e.g. a long-lived reference/demo instance).
- "No TTL policy" must read as "leave alone, no informed decision has been
  made about when this should die" — not "we don't know, so destroy it
  immediately." Treating an absent policy as an implicit "reap now" policy
  would turn a safety net into a hazard: it could destroy a real, in-use
  resource that a human deliberately created without an expiry, which is
  arguably worse than the orphan-VM incident this module exists to prevent.
- If GhostRange later wants "no TTL" to instead mean "flag for human
  review" (neither silently ignored nor silently destroyed), that is a
  distinct, deliberate policy change — this module does not make that call
  on its own initiative.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .compute_provider import ComputeProvider, WorkerHandle

logger = logging.getLogger("ghostrange.orphan_reaper")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _age_seconds(handle: WorkerHandle, now: datetime) -> float:
    created_at = handle.created_at
    if created_at.tzinfo is None:
        # Defensive: every real construction site produces tz-aware UTC
        # datetimes (ComputeRecord.created_at / utc_now()), but a
        # hand-rolled test double could hand us a naive datetime.
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (now - created_at).total_seconds()


def find_orphans(provider: ComputeProvider, *, now: datetime | None = None) -> list[WorkerHandle]:
    """Return every GhostRange-owned worker whose TTL has elapsed.

    Calls ``provider.list_all_ghostrange_workers()`` — this must be the
    *shielded/ownership-filtered* view (whatever ``build_compute_provider``
    hands back), so this function only ever sees resources GhostRange
    actually tagged as its own; it never operates on an unfiltered
    account-wide instance list.

    A handle is an orphan iff BOTH:
      - ``handle.ttl_seconds is not None`` (a TTL policy was actually set
        at creation time — see the module docstring for why a missing TTL
        is never treated as "reap immediately"), AND
      - ``(now - handle.created_at).total_seconds() > handle.ttl_seconds``
        (it has actually outlived that policy, not merely approaching it).
    """
    now = now or _utc_now()
    orphans: list[WorkerHandle] = []
    for handle in provider.list_all_ghostrange_workers():
        if handle.ttl_seconds is None:
            continue
        if _age_seconds(handle, now) > handle.ttl_seconds:
            orphans.append(handle)
    return orphans


def _handle_summary(handle: WorkerHandle, now: datetime) -> dict[str, Any]:
    return {
        "provider": handle.provider,
        "provider_compute_id": handle.provider_compute_id,
        "world_ref": handle.world_ref,
        "region": handle.region,
        "plan": handle.plan,
        "created_at": handle.created_at.isoformat(),
        "ttl_seconds": handle.ttl_seconds,
        "age_seconds": round(_age_seconds(handle, now), 3),
    }


def reap_orphans(
    provider: ComputeProvider,
    *,
    dry_run: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Find TTL-expired GhostRange workers and (unless ``dry_run``) terminate
    them through ``provider`` — which must be the shielded provider built by
    ``build_compute_provider(settings)`` (never ``RealVultrProvider`` /
    ``VultrComputeProvider`` directly), so GhostShield's ownership/policy
    checks (``P1_UNOWNED_RESOURCE`` etc.) still gate every termination
    exactly as they do for every other teardown path.

    Never raises for a single instance's termination failure — one bad
    Vultr API call must not stop the sweep from at least attempting every
    other orphan, and must not crash a caller running this on a schedule.
    Each failure is captured in the report's ``failed`` list with the error
    message; nothing is silently swallowed.

    Returns a structured report:
      - ``dry_run``: whether termination was actually attempted.
      - ``checked_at``: ISO timestamp this sweep ran at.
      - ``orphans_found``: full metadata for every TTL-expired handle found.
      - ``terminated``: provider_compute_ids successfully terminated (empty
        when ``dry_run``).
      - ``would_terminate``: provider_compute_ids that ARE orphans and WOULD
        be terminated if this were not a dry run (always populated,
        regardless of ``dry_run``, so a dry-run report is directly useful).
      - ``failed``: ``{"provider_compute_id", "error"}`` for every orphan
        whose termination raised.
      - ``still_present_after_reap``: re-check after termination — any
        provider_compute_id that was reported ``terminated`` but is STILL
        in ``provider.list_all_ghostrange_workers()`` afterward. Non-empty
        here means Vultr's own delete did not actually take effect (or
        hasn't yet); this is never assumed to have worked without checking.
    """
    now = now or _utc_now()
    orphans = find_orphans(provider, now=now)

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "checked_at": now.isoformat(),
        "orphans_found": [_handle_summary(h, now) for h in orphans],
        "terminated": [],
        "would_terminate": [h.provider_compute_id for h in orphans],
        "failed": [],
        "still_present_after_reap": [],
    }

    if not orphans:
        logger.info("orphan-reaper: sweep complete, 0 TTL-expired workers found")
        return report

    for handle in orphans:
        age_s = _age_seconds(handle, now)
        if dry_run:
            logger.info(
                "orphan-reaper: [dry_run] would terminate %s (age=%.0fs > ttl=%ss, region=%s, plan=%s)",
                handle.provider_compute_id,
                age_s,
                handle.ttl_seconds,
                handle.region,
                handle.plan,
            )
            continue
        try:
            provider.terminate_worker(handle)
        except Exception as exc:  # noqa: BLE001 - one failure must never stop the sweep
            logger.error(
                "orphan-reaper: failed to terminate %s (age=%.0fs > ttl=%ss): %s: %s",
                handle.provider_compute_id,
                age_s,
                handle.ttl_seconds,
                type(exc).__name__,
                exc,
            )
            report["failed"].append(
                {
                    "provider_compute_id": handle.provider_compute_id,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        logger.info(
            "orphan-reaper: terminated %s (age=%.0fs > ttl=%ss, region=%s, plan=%s)",
            handle.provider_compute_id,
            age_s,
            handle.ttl_seconds,
            handle.region,
            handle.plan,
        )
        report["terminated"].append(handle.provider_compute_id)

    if report["terminated"]:
        try:
            still_owned = {h.provider_compute_id for h in provider.list_all_ghostrange_workers()}
        except Exception as exc:  # noqa: BLE001 - re-check failure must not crash the sweep
            logger.error("orphan-reaper: post-reap re-check failed: %s: %s", type(exc).__name__, exc)
        else:
            report["still_present_after_reap"] = [
                cid for cid in report["terminated"] if cid in still_owned
            ]
            for cid in report["still_present_after_reap"]:
                logger.error(
                    "orphan-reaper: %s reported terminated but still present after re-check",
                    cid,
                )

    return report


__all__ = ["find_orphans", "reap_orphans"]
