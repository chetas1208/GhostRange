# Cost reconciliation

## Process

1. GhostRange calculates cost from pinned `PriceSnapshotV1` + `VultrBillingPolicySnapshot` + metered usage.  
2. When provider reports usage/cost (console, billing API, inference usage tab), ingest as **`PROVIDER_REPORTED_COST`**.  
3. If `|calculated - provider| > tolerance`, record delta — **do not silently overwrite**.  
4. Finalize campaign cost only when billable resources resolved and unknown components labeled.

## Tolerances

- Money arithmetic: **exact** (micros).  
- Provider timing lag: small temporary drift acceptable; status **`PARTIAL`**.

## Status

`CostReconciler` full implementation: **planned** (ledger preserves both fields on contracts today).
