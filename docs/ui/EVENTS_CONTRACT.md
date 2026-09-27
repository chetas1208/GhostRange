# GhostRange Event Stream Contract (Peer A proposal for Peer B)

Peer B implements `packages/events` and API transport. Peer A implements reducer in `apps/web`.

## Transport

- `GET /v1/ranges/{rangeId}/snapshot` — full normalized entity bags + `sequence` cursor.
- `GET /v1/ranges/{rangeId}/stream` — **SSE** (`text/event-stream`), ordered envelopes after snapshot (query `after=` sequence cursor).

> **2026-09-27:** Implemented transport is SSE, not WebSocket. Machine-readable catalog: `packages/events/ghostrange_events/catalog.py`.

## Envelope

```json
{
  "id": "evt-uuid",
  "sequence": 42,
  "type": "world.status_changed",
  "occurred_at": "2026-09-26T01:00:00.000Z",
  "payload": {}
}
```

Reducer must be idempotent on `id`.

## Event catalog

| type | payload |
|------|---------|
| `range.updated` | `{ range: RangeV1 }` |
| `world.created` | `{ world: WorldV1 }` |
| `world.status_changed` | `{ world_id, status, failure_reason? }` |
| `world.forked` | `{ fork: WorldForkV1, child: WorldV1 }` |
| `world.collapsed` | `{ world_id, reason, evidence_shard_id? }` |
| `asset.upserted` | `{ asset: AssetV1 }` |
| `service.upserted` | `{ service: ServiceV1 }` |
| `link.upserted` | `{ link: { id, world_id, from_id, to_id, kind } }` |
| `attack.observed` | `{ world_id, path: string[], target_asset_id }` |
| `attack.outcome` | `{ world_id, target_asset_id, outcome: AttackOutcome }` |
| `compute.worker_upserted` | `{ worker: ComputeWorkerV1 }` |
| `compute.worker_status_changed` | `{ worker_id, status }` |
| `task.upserted` | `{ task: TaskV1 }` |
| `task.status_changed` | `{ task_id, status }` |
| `scheduler.decision` | `{ decision: SchedulerDecisionV1 }` |
| `agent.upserted` | `{ agent: AgentV1 }` |
| `evidence.artifact_created` | `{ artifact: ArtifactV1, detail?: ArtifactDetail }` |
| `evidence.claim_updated` | `{ claim: ClaimV1, anchored: boolean }` |
| `evidence.verification_completed` | `{ claim_id, result: VerificationResult }` |

`ArtifactDetail` (UI-only extension for command output): `{ command?, output?, source_hostname? }`.

## Acceptance (bilateral)

- Peer B: `pytest packages/events`
- Peer A: `npm run build -w apps/web` and fixture replay populates store

Golden fixture: `apps/web/src/fixtures/demo-auth-incident-031.jsonl`
