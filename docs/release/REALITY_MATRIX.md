# GhostRange Release Reality Matrix

**Update (2026-09-27, later same day):** the "Vultr Compute workers" row below ("Not completed" / "API token ACL blocks runner; no create attempted") is superseded — a real end-to-end single-worker lifecycle has since been proven live from the control VM; see `docs/milestones/M2_CHECKPOINT_2026-09-27.md` and the authoritative `docs/milestones/M20_FINAL.md`. This was a directly-triggered single worker, not a golden-campaign-triggered one — that integrated run still has not completed.
This is the compact release-facing matrix. The detailed M20 evidence remains in [M20_REALITY_MATRIX.md](M20_REALITY_MATRIX.md).

| Subsystem | Implemented | Tested | Live | Simulated / replay | Limitation | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Local campaign API | Yes | Yes | No | Mock default | Important stages are deterministic/simulated | `scripts/m20-release-check.sh`, API tests |
| Public control VM | Yes | Health only | Controlled-live | No | Deployed API stale vs checkout | `curl /health/ready`, M20 matrix |
| Vultr Compute workers | Yes | Mock/provider tests | Not completed | Mock path | API token ACL blocks runner; no create attempted | `docs/deployment/REAL_WORKER_AUDIT.md` |
| Serverless Inference | Yes | Yes when keyed | Real-live evidence recorded | Optional | Per-request/provider billing remains distinct from Compute | M20 matrix, inference worker tests |
| PostgreSQL / Redis | Yes | Local/controlled checks | Controlled-live | No | Durable restart acceptance not run here | `main.py`, deployment docs |
| Object Storage | Yes | Adapter tests | Controlled-live | Local store | Provider-specific integration requires configured credentials | evidence/artifact modules |
| GhostDirector | Yes | Yes | No | Simulator | Not a production autonomous service | `packages/ghostdirector`, M9 docs |
| GhostScheduler | Yes | Yes | Gated | Plan/mock | Live placement proof incomplete | `packages/scheduler`, scheduler tests |
| GhostLedger | Yes | Yes | No | Local/mock | End-to-end live campaign not complete | ledger tests, M20 matrix |
| GhostShield | Yes | Yes | Not E2E | Policy simulation | Live worker path unverified | bypass/enforcement tests |
| GhostCausal | Yes | Yes | No | Simulator | No live causal campaign | M14 docs/tests |
| GhostWatch | Yes | Yes | No | Simulator | Rollout is not production | UI/API tests |
| GhostMesh | Yes | Yes | No | Five-node harness | Live federation not run | M13 docs/tests |
| GhostArena | Yes | Yes | No | Independent simulator | Not certification | M19 docs/tests |
| Tactical UI | Yes | Yes | Reachable | Fixture/replay | Human visual/tour sign-off pending | frontend tests/spec |
| Cost accounting | Yes | Yes | Conditional | Local/mock | Provider invoice reconciliation unavailable | cost tests/docs |
| Timing history | Yes | Partial | Conditional | Local/mock | Database-backed restart acceptance pending | timing store/routes |
| VKE control-plane deploy | Yes (manifests) | Yes (kustomize build + kubeconform -strict vs real k8s 1.30 schema, 11/11 valid x3 variants) | No | N/A | Real kind/k3d cluster blocked (sandbox: rootless Docker, no systemd session for cgroup delegation); real VKE cluster creation NOT_RUN, held for approval (new billable resource) | `deploy/k8s/`, `docs/deployment/VKE_DEPLOY.md`, `docs/research/VULTR.md` §6 |

