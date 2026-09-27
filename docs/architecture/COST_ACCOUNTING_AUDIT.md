# Cost accounting audit

**Date:** 2026-09-27  
**Scope:** Full-repo search for cost/pricing/usd/hourly/token/budget patterns.

## Executive finding

The previous **dominant compute formula** was:

```
estimated_cost = hourly_rate * (duration_seconds / 3600)
```

Used in `packages/scheduler/ghostrange_scheduler/cost.py` and assumed in multiple tests. Under **current Vultr server billing** (1-hour minimum quantum, billing from deploy, stopped-not-destroyed still billed), this **materially underestimates** short-lived workers and **misstates marginal reuse economics** for GhostScheduler.

**Classification:** **WRONG** for provider-authoritative compute; **APPROXIMATE** only when explicitly labeled and tied to non-Vultr mock.

---

## Inventory (selected)

| Location | Formula / behavior | Classification | Scheduler? | Budget? | UI? |
|----------|-------------------|----------------|------------|---------|-----|
| `scheduler/cost.py` (pre-fix) | `rate * sec/3600` | **WRONG** (Vultr) | YES | via est. | indirect |
| `scheduler/cost.py` (post-fix) | `ghostrange_cost` billable hours | **ESTIMATED_FROM_PROVIDER_POLICY** | YES | YES | indirect |
| `eventReducer.ts` READY/BUSY | `cost_per_hour * 0.01` | **WRONG / DEAD** | no | no | YES (removed) |
| `CostIndicator.tsx` (pre-fix) | `$${totalCostUsd.toFixed(2)}` unqualified | **WRONG UX** | no | no | YES |
| `CostIndicator.tsx` (post-fix) | Backend `/v1/ranges/{id}/cost` + semantic label | **REAL_BACKEND_DERIVED** | no | no | YES |
| `orchestrator.py` benchmark | `+= 0.024` flat increments | **APPROXIMATE** | no | no | partial |
| `compute.released` event | `total_cost_usd` float | **APPROXIMATE** | no | no | YES |
| `inference_worker_pool.py` | Flat `$0.05`/call reserve | **APPROXIMATE** (fail-closed) | no | YES | no |
| `ghostshield/policy_engine.py` | `estimated_cost_usd` float add | **APPROXIMATE** | no | YES | no |
| `ghostdirector/*` | float `estimated_cost_usd` on proposals | **UNVERIFIED** | indirect | YES | no |
| `DecisionInspector` | `$estimated_cost_usd` | **UNQUALIFIED** | display | no | YES |
| `RunBenchmark.estimated_cost_usd` | float wall-clock aggregate | **APPROXIMATE** | no | no | HUD benchmark |

---

## Duplicated / dead

| Item | Classification |
|------|----------------|
| `cost.tick` fixture event | **SIMULATED** — OK for demo |
| Client-side proration on worker READY | **DEAD** (removed) |
| `docs/architecture/COST_MODEL.md` M4 one-liner | **STALE** — superseded by `COST_ACCOUNTING.md` |

---

## Correct / keep

| Item | Notes |
|------|-------|
| GhostShield budget hard cap pattern | Keep; migrate to **USD micros + reservations** |
| Separate inference vs compute pools | **CORRECT** architecture |
| `PLACEHOLDER_RATE_CLASSES` labeling in scheduler notes | **CORRECT** honesty |

---

## Not implemented (before this pass)

- `PriceSnapshotV1` binding per resource  
- Postgres cost ledger tables  
- Provider reconciliation  
- Network egress UNKNOWN bucket  
- Warm retention / billing boundary in scheduler decisions  
- SSE `cost.snapshot.updated` from orchestrator (contract added; emission partial)

---

## Remediation delivered (Phase 1)

- New package **`ghostrange-cost`**: USD micros, Vultr policy snapshot, compute quantum, inference token math, ledger, reservations.  
- Scheduler **`estimate_cost_usd`** uses minimum billing quantum for new workers.  
- API **`GET /v1/ranges/{id}/cost`**, **`GET /v1/cost/prices/status`**.  
- UI **qualified labels**; no authoritative TS billing.  
- Tests: acceptance examples A–G + 9 unit tests in `packages/cost/tests/`.

See `VULTR_BILLING_POLICY.md`, `COST_ACCOUNTING.md`, `M20_COST_ACCOUNTING_FINAL.md`.
