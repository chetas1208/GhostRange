# Vultr billing policy (pinned)

**Policy version:** `vultr_server_billing_2025-12-16`  
**Retrieved:** 2025-12-16 (server docs); inference usage doc 2026-03-10  
**Implementation:** `ghostrange_cost.vultr_policy.DEFAULT_VULTR_POLICY`

## Official sources

| Topic | URL |
|-------|-----|
| How servers are billed | https://docs.vultr.com/support/platform/billing/how-am-i-billed-for-my-servers |
| Stopped instances still billed | https://docs.vultr.com/support/platform/billing/are-stopped-instances-still-billed-on-vultr |
| FAQ (672h vs 730h caps) | https://www.vultr.com/resources/faq/ |
| Serverless Inference usage/cost | https://docs.vultr.com/support/products/serverless/how-do-i-monitor-the-usage-and-cost-of-my-vultr-serverless-inference-subscription |

## Verified compute rules (GhostRange assumptions)

| Rule | Value |
|------|--------|
| Billing granularity | Hourly |
| Minimum billing unit | **1 hour** (all server types) |
| Billing starts | When server is **deployed** |
| Stopped but not destroyed | **Still billed** |
| Billing stops | When instance is **destroyed** (resources released) |
| Standard compute monthly cap | **672 hours/month** |
| GPU + VX1 monthly model | **730-hour industry month** (actual hours in calendar month) |

## Serverless Inference (separate product)

- Usage-based **input/output tokens** (and potentially other dimensions per model).  
- Example published rates (Mixtral 8x7B in support doc): **$0.55 / 1M input**, **$2.75 / 1M output** — bind via `InferencePriceSnapshotV1`, do not hardcode as eternal truth.  
- Release notes describe transition to per-model usage-based pricing.

## Known unknowns / reconciliation

| Component | Status |
|-----------|--------|
| Per-region plan price auto-fetch | **PRICE_RECONCILIATION_REQUIRED** without live API |
| Bandwidth egress beyond included allowance | Track usage; monetary cost when rate + usage known |
| Invoice credits / taxes | Not used for scheduler optimization |
| Plan change mid-lifetime | Split `BillingSegmentV1` (contract ready; engine partial) |

## PRICING_RECONCILIATION_REQUIRED

If provider API response contradicts pinned policy snapshot, GhostRange must **not guess** — mark reconciliation required and preserve both calculated and provider-reported amounts.
