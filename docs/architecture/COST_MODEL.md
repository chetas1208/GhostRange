# Compute cost model (M4) — superseded detail

**Authoritative doc:** [COST_ACCOUNTING.md](./COST_ACCOUNTING.md) and package **`ghostrange-cost`**.

Legacy M4 `ComputeCostModelV1` / per-second duration scaling is **deprecated for Vultr compute**. Scheduler now uses **billing quanta** via `ghostrange_cost.compute_billing`.

Semantic types: **ESTIMATED** vs **PROVIDER REPORTED** vs **FINALIZED** — never collapse unlabeled.
