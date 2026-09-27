# Real worker path audit

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
| Live billable proof on production | **MISSING** | Blocked until `VULTR_API_KEY` + VPC + deploy |

**Security:** Worker receives bootstrap token only; worker token scoped per worker. No Vultr/DB/S3 master keys on worker VM config.

**Agent 24:** **NO-GO** for live milestone until one production `live-worker-test` passes with `owned_workers == []`.
