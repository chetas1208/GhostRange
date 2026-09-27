# Live state mapping (M2 UI truth contract)

Implements **UI Specification §21** (backend event → frontend state → 3D effect). See [UI_SPECIFICATION.md](./UI_SPECIFICATION.md).

Frontend rule: **no 3D success state without a corresponding backend event** in LIVE mode. FIXTURE mode replays the same reducer path for development.

## Data sources

| Mode | Indicator | Source |
|------|-----------|--------|
| FIXTURE | HUD `FIXTURE` (amber) | `VITE_DATA_SOURCE=fixture`, JSONL replay |
| LIVE | HUD `LIVE` (mint) | SSE `/v1/ranges/{id}/stream` + snapshot |
| LIVE offline | `LIVE (offline)` | API unreachable; no invented state |

Provider badge: `MOCK` or `VULTR` from `compute.provisioning` / `compute.ready` payloads only.

## World lifecycle

| Event | Store | Component | Animation |
|-------|-------|-----------|-----------|
| `world.requested` | world record, no shell | (empty chamber) | — |
| `world.provisioning` | `shell_visible=true`, `network_ready=false` | `WorldProvisioningShell` | wireframe pulse |
| `world.ready` | `network_ready=true`, `status=READY` | `RangeWorld` + `NetworkNode`/`NetworkLink` | capsule fills |
| `world.destroyed` | `destroyed=true` | removed from scene | shell gone |

## Compute lifecycle

| Event | Worker status | Component |
|-------|---------------|-----------|
| `compute.requested` | REQUESTED | `ProvisioningGhost` (minimal wireframe) |
| `compute.provisioning` | PROVISIONING | `ProvisioningGhost` pulse |
| `compute.ready` | READY | `ComputeNode` / `CpuWorker` solid |
| task running | BUSY | utilization rise, optional `ResourceFlow` |
| `compute.released` | removed | node disappears |

Never render solid `ComputeNode` before `compute.ready`.

## Tasks & scheduler

| Event | Task status | Execution view |
|-------|-------------|----------------|
| `task.queued` | QUEUED | `ExecutionTask` |
| `task.scheduled` | SCHEDULED | edge from decision |
| `task.started` | RUNNING | pulse / trail |
| `task.completed` | COMPLETED | dimmed block |
| `scheduler.decision` | — | `DetailSurface` WHY panel |

M2 DAG order: Provision → Health → Validate → Evidence → Verify → Teardown.

## Evidence & verification

| Event | Claim / artifact | Evidence view |
|-------|------------------|---------------|
| `evidence.artifact_created` | artifact in store | `EvidenceArtifact` shard |
| `evidence.claim_updated` | claim, `anchored=false` | `ClaimNode` wobble |
| `verification.started` | — | `VerificationRing` begins |
| `verification.passed` | `anchored=true` | ring locks, mint accent |
| `evidence.created` | provenance link | constellation edge |

## Reducer

All envelopes normalized via `normalizeEnvelope.ts` → `eventReducer.ts`. Legacy M1 event names remain supported for the old demo fixture (`VITE_FIXTURE=m1`).

See also [EVENTS_CONTRACT.md](./EVENTS_CONTRACT.md) and [THREE_D_ARCHITECTURE.md](./THREE_D_ARCHITECTURE.md).
