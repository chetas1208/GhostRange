# M17 GhostShield — final report (Agent 52)

**Decision: NO-GO** (2026-09-27)

## What is GhostShield?

Deterministic policy engine + execution gateway that authorizes **typed canonical actions** before high-consequence provider effects. LLM/Director/Scheduler are proposers only.

## TCB

`GhostShieldPolicyEngine`, `GhostExecutionGateway`, future signed policy bundle + canonical Postgres revisions.

## Canonical action / policy / permit

Defined in `ghostshield_m17.py`. Permit binds digest, principal, policy version, state revision, campaign, expiry; gateway rejects mutation, replay (single-use), stale revision, and re-evaluates fleet limits at execution (TOCTOU for P2).

## Protected actions

Worker **create/terminate** on scheduler API path when `GHOSTSHIELD_MODE≠DISABLED`. **Not** full range provisioning or orchestrator golden path.

## Bypass

**Yes — alternate paths remain:** `orchestrator.py`, `range-runtime/vultr_adapter.py`. Static test prevents *new* API imports of `RealVultrProvider`.

## Formal

`WorkerFleet.tla` + cfg; **TLC not executed** — no state counts, no counterexamples.

## Real bug from formal

**None found.**

## Metrics (simulator / unit)

| Metric | Value |
|--------|-------|
| Unsafe action allow rate (ENFORCE mock corpus) | 0 on second-worker test |
| Bypass rate (worker path) | 0 when ENFORCE + shield wrapper |
| False deny rate | Not measured at scale |
| Auth latency p50/p95/p99 | Not measured |

## Live Vultr ENFORCE

**Not run** — Vultr API ACL + M16 journal incomplete; `owned_workers == []` live not re-verified under ENFORCE.

## Prompt injection / compromised scheduler

Unit policy: over-limit create → **DENY** before effect; no provider call in gateway ENFORCE path.

## Agent 52 automatic NO-GO triggers hit

- Alternate Vultr paths bypass gateway
- Live ENFORCE acceptance incomplete
- Model-check artifacts absent
- Canonical runtime revision not Postgres-backed

## M18 should

1. Close bypasses (orchestrator + range-runtime through gateway).
2. Wire M16 side-effect journal + `runtime_revision` from Postgres.
3. TLC in local CI; lease/recovery TLA module; counterexample → regression.
4. Live ENFORCE with `MAX_ACTIVE_WORKERS=1` after Vultr ACL fix.
5. GhostLedger `AuthorizationEvidenceV1` persistence + Evidence UI property rows.
