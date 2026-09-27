# Cost accounting architecture

## Canonical representation

- **USD_MICROS** — integer microdollars (`1 USD = 1_000_000` micros).  
- **No float** in authoritative ledger math (`ghostrange_cost.money`).

## Semantic types (UI + API)

Every displayed dollar amount must identify:

- `PROJECTED_COST`
- `RESERVED_COST`
- `ACCRUED_ESTIMATE`
- `PROVIDER_REPORTED_COST`
- `INVOICED_COST`

Campaign snapshots default to **`ACCRUED_ESTIMATE`** until finalized.

## Compute (Vultr ephemeral VM)

Authoritative estimate:

```
billable_hours = f(provider_lifetime_seconds, minimum_quantum=1h)
compute_usd_micros = billable_hours * hourly_rate_usd_micros
```

**Not:** `lifetime_seconds / 3600 * rate` for provider billing.

Lifecycle timestamps drive lifetime (`create_requested_at` … `provider_destroyed_at`). Delete request without destroy confirmation → **`BILLING_END_UNCONFIRMED`**.

## Inference

```
input_cost = input_tokens * input_price_per_million / 1_000_000
output_cost = output_tokens * output_price_per_million / 1_000_000
```

Integer/Decimal only. Missing model price → **`PRICE_UNKNOWN`**, never `$0`.

## Resource cost vs attribution

- **ResourceCostRecordV1** — one row per billable VM / metered service.  
- **CostAttributionV1** — analytical split across tasks; campaign total = **sum of unique resources**, not sum of attributions.

## GhostScheduler

- **New worker:** at least one billing quantum (`estimate_cost_usd`, `estimate_marginal_new_worker_usd`).  
- **Reuse:** `estimate_marginal_reuse_usd` — near-zero incremental cost inside committed quantum.  
- Optimize **incremental future cost**, not sunk spend.

## GhostCostLedger

The mutation core is process-local (`apps/api` `app.state.cost_ledger`), with
optional PostgreSQL snapshot persistence through
`apps/api/ghostrange_api/cost_persistence.py`. The API initializes the schema,
restores the latest serialized ledger state, and saves after cost snapshot
events when durable PostgreSQL is configured. A full provider-normalized
relational ledger (`price_snapshots`, `resource_cost_records`, billing
segments, campaign snapshots, and reconciliations) is still future work.

## API

- `GET /v1/ranges/{id}/cost` — canonical campaign snapshot  
- `GET /v1/cost/prices/status` — pinned policy metadata  

Frontend: **`useCampaignCost`** — display only.

## Events

- `cost.snapshot.updated` — reducer updates HUD semantic type + micros (no client-side billing).

## Related

- `COST_ACCOUNTING_AUDIT.md`
- `GHOSTSCHEDULER_COST_MODEL.md`
- `docs/ui/COST_VISUALIZATION.md`

## Provider billing source

The Compute policy is pinned to [Vultr's official server billing
documentation](https://docs.vultr.com/support/platform/billing/how-am-i-billed-for-my-servers): Cloud Compute servers use a one-hour minimum billing unit and continue billing while stopped until destroyed. [Serverless Inference is token-metered by input/output usage](https://docs.vultr.com/support/products/serverless/how-do-i-monitor-the-usage-and-cost-of-my-vultr-serverless-inference-subscription). The implementation records the policy snapshot and keeps provider invoice-level reconciliation explicit as unavailable when the API does not provide campaign totals.
