# Real worker milestone — final report

**Update (2026-09-27, later same day):** the "live proof" gaps this file originally recorded as NO-GO
were closed the same day. A real Vultr Compute VM was created, bootstrapped, ran a real CPU benchmark
(2,000,000 iterations, 436ms) with the result stored as a real Postgres artifact row, torn down, and its
deletion confirmed via a direct per-resource Vultr GET returning 404. See
`docs/milestones/M2_CHECKPOINT_2026-09-27.md` ("Real infrastructure proof") and the current
`docs/milestones/M20_FINAL.md` for the authoritative status. The table below is preserved as the
point-in-time record that preceded that proof; it no longer reflects current reality. Note this remains a
**single directly-triggered worker lifecycle**, not a golden-campaign-triggered live worker — that
integrated run still has not completed (see `docs/milestones/M20_FINAL.md`).

## What was built

- Worker API (`/v1/workers/*`), bootstrap agent download, Postgres worker/task/lease tables.
- `RealWorkerOrchestrator`: one run, one worker, one CPU task, artifact via control plane, teardown.
- Mock path runs in-process `ghostrange_worker` against the API (no Vultr bill).
- Live path: cloud-init + `deploy/worker/worker_agent.py` + `POST /v1/scheduler/live-worker-test?live=true&confirm=true`.

## Boot / register / auth / lease

See `worker_orchestrator.py`, `worker_store.py`, `worker_routes.py`, `cloud_init.py`.

## Live proof status

| Check | Mock (local/CI) | Live Vultr |
|-------|-----------------|------------|
| Task on worker | yes (runtime) | **not verified** |
| S3 artifact | yes if S3 configured | **not verified** |
| PG state | yes if DATABASE_URL | **not verified** |
| Teardown + owned_workers=[] | yes | **not verified** |

## Agent 24 decision

**NO-GO** — live billable acceptance test has not been executed in this environment (compute API key / VPC / deploy gate).

## To unlock GO

1. Set on `ghostrange-control`: `VULTR_API_KEY`, `GHOSTRANGE_WORKER_VPC_ID`, `GHOSTSCHEDULER_LIVE=true`, `GHOSTRANGE_PUBLIC_URL=http://45.76.248.45`.
2. Deploy API image with worker tables migrated (Postgres schema apply on startup).
3. Run: `GHOSTRANGE_BASE_URL=http://45.76.248.45 bash scripts/real-worker-e2e.sh --live`
4. Confirm dry-check `owned_worker_count=0` and artifact row exists.

## Remains stubbed

- UI worker geometry from live events; startup reconciliation; presigned direct-to-S3 worker uploads; red-team automation.
