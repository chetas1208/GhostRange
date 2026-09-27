# M20 live event inventory (implementation truth)

Status key: **WIRED** | **PARTIAL** | **UNWIRED** | **UNUSED**

| Event | Source | Reducer | 3D/DOM | Screenshot deps |
|-------|--------|---------|--------|-----------------|
| `golden_path.phase` | golden_path | WIRED | timeline | 02–04 |
| `director.decision` | golden_path | PARTIAL | timeline marker | 04 hypotheses |
| `scheduler.plan` | golden_path | WIRED | decisions stub | 08–10 |
| `ghostledger.sealed` | golden_path | WIRED | verification ring | 20 |
| `campaign.phase` | m20_campaign | WIRED | HUD, arena | 21, 24 |
| `world.*` | M2 orchestrator | WIRED | WorldShell/Birth | 02, 05, 23 |
| `compute.*` | M2 orchestrator | WIRED | WorkerNode | 07, 23 |
| `task.*` | M2 orchestrator | WIRED | TaskNode/DAG | 06 |
| `scheduler.decision` | M2 orchestrator | WIRED | SchedulerDecisionMarker | 08 |
| `evidence.created` | M2 orchestrator | PARTIAL | Evidence | 19 |
| `verification.*` | M2 orchestrator | WIRED | VerificationRing | 20 |
| `world.fork.created` | multiverse API | WIRED | WorldFork | 14–15 |
| `execution.denied` | m20_ui_events | WIRED | ActionGate | 18 |
| `causal.*` | m20_ui_events | WIRED | CausalPath | 13–14 |
| `adversarial.counterexample` | m20_ui_events | WIRED | claims/timeline | 16 |
| `runtime.interruption` / `runtime.recovered` | m20_ui_events | WIRED | FailureFracture | 11–12 |
| `attack.observed` | m20_ui_events | WIRED | AttackPath | 03 |

## Bootstrap contract

1. `GET /v1/ranges/{id}/snapshot` → apply all events, set `lastEventSeq`
2. `EventSource /v1/ranges/{id}/stream?after={seq}` → apply only newer seq / new event_id
3. `POST /v1/campaigns/golden` → reset client store → connect stream on returned `range_id`
4. M2 `start_run(range_id)` chained after golden (same range) for worker/DAG/evidence events

## Idempotency

- Reducer skips duplicate `event.id` (`processedEventIds`)
- `compute.ready` ignored after `compute.released` / destroying terminal states
