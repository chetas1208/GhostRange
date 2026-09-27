# M16 final report (draft — Agent 50)

## Agent 50 decision

**NO-GO** — GhostRuntime contracts and adopt-worker recovery policy exist; **no** live chaos, **no** side-effect journal wired to Vultr, **no** checkpoint/replay integration, **no** horizon reliability benchmark corpus.

## What is GhostRuntime? (target)

Durable execution substrate under campaigns: canonical PostgreSQL state, side-effect intent journal, checkpoints, deterministic replay (frozen model outputs), reconciliation with Vultr/S3, safe mode, recovery manager — **without** a new reasoning subsystem.

## What exists after Wave 0–1 bootstrap

- Contracts: `ghostruntime_m16.py` (Wave 1 freeze set started).
- Schema: `campaign_runtime`, `runtime_side_effects`, `runtime_checkpoints`, `runtime_events`, `task_attempts`, `canonical_task_results`, `runtime_recovery_runs`.
- Package: `ghostrange-ghostruntime` with `CampaignRecoveryManager` (adopt-worker + safe-mode decisions).
- Tests: M16 contract + recovery unit tests.
- Docs: audit, coordination (50 agents), reliability synthesis.

## Execution guarantee (stated honestly)

**Effectively-once outcomes** via idempotent commit — **not** exactly-once execution.

## Live chaos

| Test | Status |
|------|--------|
| A — API restart during task | NOT RUN |
| B — crash after Vultr create, before DB | NOT RUN (policy tested in unit tests only) |
| C — VM reboot | NOT RUN |
| `ALLOW_M16_LIVE_CHAOS` | unset / false |

## Metrics

Duplicate effect rate, orphan rate, MTTR, horizon decay — **not measured yet**.

## What should M17 do?

TBD after M16 GO — candidate: closed-loop **horizon reliability benchmarks** tied to GhostLedger provenance exports, or completion of M15 live scheduler once worker GO unblocks.
