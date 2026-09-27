# Formal model ↔ production mapping

| Production | TLA+ (`WorkerFleet.tla`) |
|------------|---------------------------|
| `active_workers` | `active` |
| `MAX_ACTIVE_WORKERS` | `max` |
| `CREATE_WORKER` (allowed) | `CreateWorker` |
| `CREATE_WORKER` (denied) | `CreateWorkerBlocked` |
| `TERMINATE_WORKER` | `TerminateWorker` |

**Omitted:** Postgres revision, permits, gateway, leases, recovery, provider delay/duplicate (future modules).

**Limitation:** Model proves `active <= max` on abstract transitions, not full GhostRange safety.
