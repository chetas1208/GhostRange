# M20 cost accounting — final report

**Status:** Phase 2 core complete; Postgres ledger + provider invoice reconciliation remain.

## Completed (this chat backlog)

- [x] Provider billing policy pinned (`VULTR_BILLING_POLICY.md`, `ghostrange_cost.vultr_policy`)
- [x] No canonical float money (`USD_MICROS`)
- [x] Price snapshot contracts (`PriceSnapshotV1`, `InferencePriceSnapshotV1`)
- [x] Compute billing quantum (not per-second)
- [x] Stopped / destroy-unconfirmed semantics in accrual helper
- [x] Worker reuse vs campaign total (attribution separate)
- [x] Speculation = multiple resources in tests
- [x] Retries/failed attempts counted in inference spend path
- [x] Budget reservation + concurrent race test
- [x] Scheduler quantum + marginal reuse helpers
- [x] `WarmRetentionDecisionV1` helper (`warm_retention.py`)
- [x] Orchestrator → ledger via `CostAccountingBridge`
- [x] SSE `cost.snapshot.updated` on compute ready/release
- [x] API cost + price status + timing decomposition route
- [x] Inference token metering when `usage` present in response
- [x] UI qualified cost labels + `CostInspector`
- [x] Unit/invariant/acceptance tests (24+ in cost package + API)

## Tests (verified)

```bash
pytest -q packages/cost/tests                          # 11 passed
pytest -q apps/api/tests/test_cost_routes.py \
         apps/api/tests/test_cost_bridge_sse.py \
         apps/api/tests/test_worlds_routes.py          # pass
pytest -q packages/scheduler/tests/test_cost.py \
         packages/scheduler/tests/test_warm_retention.py
npm run typecheck && npm run test -w apps/web
```

## Still human / infra dependent

- [ ] Postgres migrations for durable ledger
- [ ] Provider invoice reconciliation (`CostReconciler` service)
- [ ] GPU product-class-specific cap routing in production
- [ ] Full scheduler benchmark re-run published in `COST_MODEL_CORRECTION_IMPACT.md`
- [ ] Hackathon credits / account-level billing UI (only if API available)

## Answers (§112 summary)

| Question | Answer |
|----------|--------|
| Old model wrong? | Per-second VM proration |
| Vultr min unit | 1 hour |
| Billing start/stop | Deploy → destroy confirmed |
| Stopped billed? | Yes until destroyed |
| Inference | Token metered; snapshot rates |
| Scheduler marginal | `estimate_marginal_*` + warm retention helper |
| UI authority | Backend `/v1/ranges/{id}/cost` only |
