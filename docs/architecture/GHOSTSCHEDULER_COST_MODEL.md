# GhostScheduler cost model (post quantum correction)

## Decision inputs

Each cost-sensitive `SchedulerDecisionV1` should eventually include:

- price snapshot id  
- startup / runtime estimates  
- **committed** cost on candidate worker  
- **incremental future** cost  
- projected campaign total  
- budget remaining  

Phase 1 exposes functions on `ghostrange_scheduler.cost`:

| Function | Meaning |
|----------|---------|
| `estimate_cost_usd(class, duration, cluster)` | New worker: duration bounded by **≥1h quantum** |
| `estimate_marginal_new_worker_usd(class, cluster)` | Scale-out: +1 minimum quantum |
| `estimate_marginal_reuse_usd(...)` | Task on warm worker inside current quantum |

## One-hour minimum consequence

Worker alive 10 minutes → **1 hour committed**. A compatible 5-minute task on that worker may have **~$0 incremental compute** vs provisioning another VM.

Warm retention decisions should use `seconds_to_next_billing_boundary` (see `CostStateV1` contract).

## Speculation

Primary + speculative workers = **two billable resources**. Both quanta count toward campaign cost.

## Budget enforcement

Use **conservative projected cost** including minimum quantum for new resources.  
**CostReservationV1** prevents concurrent over-commit (`GhostCostLedger.reserve`).

## Scheduler basis

Optimize **resource economic cost** (pre-tax, pre-credit), not invoice balance after promotional credits.
