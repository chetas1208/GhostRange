# Real worker path audit

**Update (2026-09-27, later same day):** "Live billable proof on production" below is superseded — a
real Vultr Compute VM was created, bootstrapped, benchmarked (2,000,000 iterations, 436ms, real Postgres
artifact row), torn down, and confirmed destroyed via a direct Vultr GET returning 404. See
`docs/milestones/M2_CHECKPOINT_2026-09-27.md` and `docs/milestones/M20_FINAL.md`. This was a single
directly-triggered worker, not a golden-campaign-triggered one; that integrated run still has not
completed.

| Component | Classification | Notes |
|-----------|----------------|-------|
| `compute_provider.py` Mock/Vultr | **READY** | `user_data`, tags, destroy confirms absence |
| `worker_scheduler.py` | **REAL** | Delegates to orchestrator; mock vs live gated |
| `worker_orchestrator.py` | **REAL** | Provision → register → lease → task → teardown |
| `worker_store.py` | **REAL** | Bootstrap, lease, heartbeat, tasks |
| `worker_routes.py` | **REAL** | Narrow worker API + bootstrap agent bundle |
| `worker_auth.py` | **REAL** | SHA-256 hashed tokens |
| `cloud_init.py` + `deploy/worker/worker_agent.py` | **REAL** | No long-lived secrets in user-data |
| `packages/worker-runtime` | **REAL** | Poll/lease/CPU benchmark for mock path |
| `worker-benchmark` endpoint | **REAL** | Mock runtime E2E (no billable VM) |
| `live-worker-test` | **READY** | Double gate `live` + `confirm`; needs deploy + secrets |
| `VultrComputeProvider.run_benchmark` | **STUB** | Unused when orchestrator path active |
| UI Execution worker geometry | **PARTIAL** | Backend events exist; UI not wired this milestone |
| Startup reconciliation | **MISSING** | Nonterminal runs not auto-reconciled yet |
| Presigned worker S3 upload | **MOCK** | Backend-mediated upload via artifact registry |
| Live billable proof on production | **DONE (2026-09-27)** | Real create→bootstrap→benchmark→teardown→confirmed-destroyed lifecycle proven; see update note above. Golden-campaign-triggered live worker still not proven. |

**Security:** Worker receives bootstrap token only; worker token scoped per worker. No Vultr/DB/S3 master keys on worker VM config.

**Agent 24 (superseded 2026-09-27):** originally **NO-GO**; a production `live-worker-test`-equivalent lifecycle has since passed with the destroyed instance confirmed absent via a direct Vultr GET (404). Remaining gap is the golden-campaign integration, not the worker path itself.
