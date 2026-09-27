# M12 Coordination — GhostWatch (38 specialists)

**Default authority:** `OBSERVE_ONLY`. No subagent assumes production access.

| Wave | agents | focus |
|------|--------|--------|
| 0 | 01–02 | Audit + research |
| 1 | 03–06, 10, 12 | Authority + contracts |
| 2 | 07–09, 11, 13–14 | Adapters + observability |
| 3 | 15–19 | Canary / rollback logic |
| 4 | 20–26 | Evidence + twin loop |
| 5 | 27–30 | Simulator + UI |
| 6 | 31–34 | Security + benchmark |
| 7 | 35 | Ops docs |
| 8 | 36 | GO/NO-GO |

| ID | mission | owned_paths | status |
|----|---------|-------------|--------|
| 01 | Audit | `M12_AUDIT.md` | done |
| 02 | M11 blocker closure | `ghostgate/recompile.py`, verify API | partial |
| 03 | Research | `M12_GHOSTWATCH_SYNTHESIS.md` | done |
| 03 | Authority | `authority.py`, `DEPLOYMENT_AUTHORITY.md` | done |
| 04 | Execution contracts | `ghostwatch_m12.py` | done |
| 05 | Conformance | `conformance.py` | done |
| 06 | Adapter model | `adapters/base.py` | done |
| 07 | Argo adapter | stub | deferred |
| 08 | Generic adapter | `adapters/generic.py` | done |
| 09 | Feature flags | stub OpenFeature notes | partial |
| 10–12 | Obs + invariants | `observability/mock.py`, `invariants.py` | done |
| 13 | Synthetic tx | `synthetic.py` | done |
| 14 | Baseline | `baseline.py` | done |
| 15 | Canary analysis | `canary_analysis.py` | done |
| 16–19 | Telemetry/rollback | `rollback.py` | done |
| 20–21 | Evidence/ledger | `evidence.py` | partial |
| 22–26 | Twin/Director bridges | `surprise.py`, `director_bridge.py` | partial |
| 27 | Simulator | `simulator.py` | done |
| 28–30 | UI | `GhostWatchPanel.tsx` | started |
| 31–34 | Security/benchmark | tests + `benchmark_m12.py` | done |
| 35 | Ops | `OPERATIONS_GHOSTWATCH.md` | done |
| 36 | Review | `M12_FINAL.md` | NO-GO |
