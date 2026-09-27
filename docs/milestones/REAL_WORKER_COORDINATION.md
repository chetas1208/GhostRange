# Real worker coordination (24 agents)

**Update (2026-09-27, later same day):** agent 24's live-proof blocker (row below) is closed — a real
Vultr Compute worker lifecycle completed and was independently verified. See
`docs/milestones/M2_CHECKPOINT_2026-09-27.md` and `docs/milestones/M20_FINAL.md`. This was a single
directly-triggered worker; a golden-campaign-triggered live worker as one integrated run still has not
completed.

| agent_id | mission | owned_paths | status | integration |
|----------|---------|-------------|--------|-------------|
| 01 | Audit existing path | `docs/deployment/REAL_WORKER_AUDIT.md` | done | pass |
| 02 | Worker contracts | `worker_models.py` | done | pass |
| 03 | State machine | `worker_models.py`, `worker_store.py` | done | pass |
| 04 | Bootstrap token | `worker_auth.py`, `worker_store.py` | done | pass |
| 05 | Cloud-init | `cloud_init.py`, `deploy/worker/` | done | pass |
| 06 | Worker runtime | `packages/worker-runtime/` | done | pass |
| 07 | Systemd | `cloud_init.py` | done | pass |
| 08 | Worker auth | `worker_routes.py`, `worker_auth.py` | done | pass |
| 09 | Task contract | `worker_store.py` | done | pass |
| 10 | Lease | `worker_store.py` | done | pass |
| 11 | Heartbeat | `worker_store.py`, `worker_routes.py` | done | pass |
| 12 | CPU benchmark | `benchmark.py`, `worker_agent.py` | done | pass |
| 13 | Artifact upload | `worker_routes.py`, `artifact_registry.py` | done | pass |
| 14 | Postgres run state | `schema.sql`, `worker_store.py` | done | pass |
| 15 | Vultr provider | `compute_provider.py` | done | pass |
| 16 | Ownership/TTL | tags + `max_worker_lifetime_minutes` | partial | pass mock |
| 17 | Cost guardrails | `scheduler_routes`, `worker_scheduler` | done | pass |
| 18 | Reconciliation | — | blocked | missing |
| 19 | Failure cleanup | `worker_orchestrator` finally | done | pass mock |
| 20 | API integration | `scheduler_routes`, `main.py` | done | pass |
| 21 | Execution UI | `apps/web` | deferred | stub |
| 22 | Live E2E script | `scripts/real-worker-e2e.sh` | done | pass mock |
| 23 | Red team | manual | pending | not run |
| 24 | Final reviewer | `REAL_WORKER_FINAL.md` | **GO (single worker, 2026-09-27)** | live proof done; golden-campaign integration still pending |

Blockers (resolved 2026-09-27 for the single-worker path): production deploy of new API image; `VULTR_API_KEY`; `GHOSTRANGE_WORKER_VPC_ID`; `GHOSTSCHEDULER_LIVE=true`; `GHOSTRANGE_PUBLIC_URL`. Remaining blocker: the golden campaign (`POST /v1/campaigns/golden`) still does not successfully trigger a live worker as part of one integrated run.
