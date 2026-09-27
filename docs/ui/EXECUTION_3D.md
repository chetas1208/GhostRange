# Execution 3D (tactical)

## Question answered

**What is GhostRange doing right now, step by step?**

## Scene ownership

- `ExecutionScene.tsx` — scheduler floor, tasks, workers, authorization gate, resource flows.
- DOM: `DetailSurface`, `DecisionInspector`, mission tree patterns in FINAL UI spec.

## Truth sources

- Task DAG from `task.*` events and M2 ordering helper `selectM2ExecutionTasks`.
- Scheduler decisions from `scheduler.decision` → `decisions` store.
- Timers: event timestamps + optional `GET /v1/ranges/{id}/benchmark`.

## Not yet

Per-server queue, queue-wait ms, GPU telemetry — see audit.
