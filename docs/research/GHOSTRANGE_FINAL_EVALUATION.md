# GhostRange final evaluation summary (M20)

## RQ status (honest)

| RQ | Status | Notes |
|----|--------|-------|
| RQ1 Twin reduces unnecessary experiments | PARTIALLY_SUPPORTED | Director stops with budget; no A/B vs no-twin study |
| RQ2 Causal vs correlation | PARTIALLY_SUPPORTED | GhostCausal sim; not in M20 golden HTTP |
| RQ3 Adaptive scheduling cost/latency | PARTIALLY_SUPPORTED | Scheduler V3 benchmarks M15; golden uses plan-only |
| RQ4 Durable execution under failure | UNSUPPORTED in M20 demo | Runtime tests local only |
| RQ5 Shield blocks unsafe model actions | PARTIALLY_SUPPORTED | policy tests; bypass routes remain |
| RQ6 Self-improvement without hidden regression | PARTIALLY_SUPPORTED | Arena rejects `fast_premature` (sim) |
| RQ7 Arena detects overfitting | SUPPORTED (sim) | M19 negative case documented |

## Negative results (required)

- M17 GhostShield: **NO-GO** (bypass paths).
- M18 GhostEvolve: **NO-GO** (no live shadow/canary).
- M19 GhostArena: **NO-GO** (no live range qualification).
- Live worker E2E: **blocked** by Vultr Compute API IP ACL on control VM.
- M20 live golden campaign: **NOT_RUN** without `ALLOW_M20_LIVE_CAMPAIGN` + ACL fix.

## Arena on release candidate (sim)

Current build evaluated with `candidate_policy=qualified` → **QUALIFIED** (sim hidden suite only — not a production ship gate alone).
