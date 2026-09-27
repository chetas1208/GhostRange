# M6 Audit — Wave 0 (2026-09-26)

Verified repository before Living Twin work. Prior milestone finals are mostly **stubs**; capability is ahead of `Progress.md` in some areas and behind in others.

## Commands run

| Check | Result |
|-------|--------|
| `npm run typecheck` | pass (prior session) |
| `pytest packages/contracts -q` | 76 pass |
| `pytest packages/range-compiler -q` | 6 pass |
| `pytest packages/scheduler -q` | 119 pass |
| `git log` | **no commits** |

## M5 reality (M6 dependency)

| Area | Classification |
|------|----------------|
| `NormalizedSystemGraphV1` | **IMPLEMENTED** — Compose/TF/K8s → graph |
| `RangeCompiler` pipeline | **PARTIAL** — to RangeSpecV2, no live deploy |
| `FidelityReportV1` gates | **PARTIAL** — heuristic scores, no live twin validation |
| Source revision tracking | **BLOCKING_M6** — not present pre-M6 |
| Claim assumptions / validity | **BLOCKING_M6** — `ClaimV1` has no STALE/INVALIDATED |
| M3 live multiverse | **NOT COMPLETE** — revalidation re-entry depends on orchestrator later |

## Ready for M6

- System graph node/edge kinds align with M6 semantic drift categories  
- Fidelity dimensions (M5) map to investigation-dependent impact  
- `ghostrange-range-compiler` can produce two graphs from two compose revisions  
- GhostScheduler V3 `plan()` can schedule revalidation workloads (extend in Wave 3)

## M6 blockers to clear

1. **SourceRevisionV1 / TwinRevisionV1** lineage  
2. **Semantic graph diff** (not text diff)  
3. **ImpactGraphV1** + rules  
4. **AssumptionV1** + claim validity lifecycle  
5. **RevalidationPlanV1** + incremental compile plan  
6. API + events (Wave 4+)  
7. UI SourceGhost drift (Wave 5)

## Security (M6)

- No production mutation, no secret sync, read-only source watch — **policy required from day one** (`config/living-twin-policy.yaml`).
