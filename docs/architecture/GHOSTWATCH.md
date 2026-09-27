# GhostWatch (M12)

GhostWatch observes **externally initiated** deployments that match an M11 **approved** promotion package.

## vs GhostGate

| GhostGate (M11) | GhostWatch (M12) |
|-----------------|-------------------|
| Builds change package | Observes rollout after external executor starts |
| Human approval before deploy | Binds to `change_candidate_hash` + approval |
| No production touch | Read-only default; optional **preauthorized** rollback |

## Default authority

`OBSERVE_ONLY` — recommend only. Kill switch: `GHOSTWATCH_CONTROL_DISABLED=true`.

## Adapters

- `MockDeploymentExecutorAdapter` — `SIMULATED_ROLLOUT`
- Generic signed status adapter (future)
- Argo Rollouts (controlled env, future)

## API

- `POST /v1/ghostwatch/simulate` — full scenario in simulator
- `POST /v1/ghostwatch/campaigns/start` — bind to promotion candidate
- `GET /v1/ghostwatch/campaigns/{id}`

## Closed loop

Production surprise → `director_bridge` → **disposable** experiment proposal only.
