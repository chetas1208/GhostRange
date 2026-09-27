# GhostRange Release Reality Matrix

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

