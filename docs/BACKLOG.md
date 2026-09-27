# GhostRange master backlog (consolidated)

**50 workstreams** — status updated 2026-09-27 — see `docs/SESSION_TRACE.md`.

Legend: **done** · **partial** · **open**

## Repo (5)

1. First git commit baseline — **open** (user decision)  
2. Refresh `Progress.md` — **partial** (see `docs/INTEGRATION_STATUS.md`)  
3. Rename duplicate `test_scheduler.py` — **done**  
4. Postgres EventGateway as API default — **open**  
5. `INTEGRATION_STATUS.md` maintenance — **done** (initial)  

## M2 finish (5)

6. Live Vultr one-world E2E — **open** (live guard exists)  
7. Policy execution events — **partial**  
8. Serverless inference planner — **open**  
9. `packages/adversary-adapter` — **partial** (Caldera client + safety tests)  
10. `packages/execution-graph` runtime — **partial** (DAG topo + cycle tests)  

## M3 multiverse (10)

11. Fork orchestrator (3 worlds) — **partial** (API + mock events)  
12. GhostScheduler V2 runtime — **open** (use V3)  
13. Attack replay + regression per world — **open**  
14. Evidence namespace isolation — **open**  
15. M3 events + idempotency — **partial**  
16. Live multiverse UI — **partial** (fork events + tactical 3D orbit; see TACTICAL_UI_FINAL)  
17. M3 benchmarks — **open**  
18. M3 live screenshots — **open**  
19. `M3_FINAL.md` — **open**  
20. Orphan scanner multi-world — **open**  

## M4 scheduler (10)

21. Straggler + speculation modules — **open**  
22. Autoscale + fragmentation — **partial** (V3 plan)  
23. Adaptive inference budget — **open**  
24. Benchmark matrix → `artifacts/benchmarks/m4/` — **open**  
25. `GET /scheduler/*` API — **partial** (`POST /v1/scheduler/plan-preview`)  
26. Execution UI ← V3 decisions — **partial** (Director/Scheduler strip)  
27. Vultr calibration — **open**  
28. `M4_BENCHMARK_REPORT.md` — **open**  
29. `M4_FINAL.md` gate — **open**  
30. Scheduler decision persistence — **open**  

## M5 compiler (10)

31. Live provision from RangeSpecV2 — **open**  
32. Multi-source merge — **open**  
33. `ghostrange.yaml` blueprint — **open**  
34. External stub + network safety — **partial**  
35. Behavioral invariant runtime — **open**  
36. SourceShadow UI — **open**  
37. Compiler API + events — **partial** (golden path compile)  
38. M5 benchmarks — **open**  
39. Compiled world → verification E2E — **partial**  
40. `M5_FINAL.md` gate — **open**  

## M6 living twin (10)

41. Source watch (Git/manual) — **open**  
42. API `POST .../revisions` — **open**  
43. Drift domain events — **open**  
44. Assumption persistence + evidence context — **open**  
45. Scheduler revalidation tasks — **open**  
46. Multiverse drift visuals — **open**  
47. Evidence staleness/supersession UI — **open**  
48. M6 mutation goldens (full corpus) — **partial**  
49. M6 benchmarks — **open**  
50. `M6_FINAL.md` + live experiment — **open**  

## M10 integration (added)

51. Golden path SSE events — **done**  
52. `make test` / `run-all-tests.sh` — **done**  
53. Live golden + lease — **partial**  
54. Agent 40 GO — **NO-GO** (see `M10_FINAL.md`)  

**Current focus:** Close M10 gate items without new subsystems — chain M2 run after golden path, live run once, UI LIVE wiring.
