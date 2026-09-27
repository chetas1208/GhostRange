# M10 Coordination — One System (40 specialists)

Lead owns integration, contract arbitration, release gate, **single live resource lease** (no parallel agent provisioning).

## Waves

| Wave | agents | focus |
|------|--------|--------|
| 0 | 01–04 | Audit, architecture, contracts, events |
| 1 | 05–11 | Compiler, fidelity, Vultr, worlds, fork |
| 2 | 12–17 | Scheduler, Director, inference, policy |
| 3 | 18–23 | Incident, remediation, verify, adversarial, living twin |
| 4 | 24–30 | Evidence, ledger, DB, SSE, observability, cost |
| 5 | 31–35 | UI release, perf, a11y |
| 6 | 36–38 | Chaos, security, benchmarks |
| 7 | 39 | Release packaging |
| 8 | 40 | Independent GO/NO-GO |

## Agent roster (abbreviated status — Wave 0 complete)

| ID | mission | owned_paths | status |
|----|---------|-------------|--------|
| 01 | Audit + matrix | `M10_AUDIT.md`, `M10_CAPABILITY_MATRIX.md` | done |
| 02 | System architecture | `M10_SYSTEM_ARCHITECTURE.md` | done |
| 03 | Contract consistency | `M10_CANONICAL_CONTRACTS.md` | done |
| 04 | Event consistency | `director_events`, adversarial_events audit | partial |
| 05 | Compiler integration | `golden_path.py`, auth-platform-v2 | started |
| 06 | Fidelity integration | golden path gate | started |
| 07 | Vultr control | `orchestrator.py`, live guard | partial |
| 08 | Templates/clusters | defer doc | planned |
| 09 | Network isolation | security tests | planned |
| 10 | World runtime | range-runtime | partial |
| 11 | World fork | M3 runtime | planned |
| 12 | Scheduler integration | golden path handoff | started |
| 13 | Scheduler perf | benchmarks/m10 | planned |
| 14 | Director integration | `golden_path.py` | started |
| 15 | Director safety | `validate.py` tests | partial |
| 16 | Serverless inference | stub | planned |
| 17 | Execution policy | policy-check audit | planned |
| 18 | Controlled incident | auth-lab scenario | partial |
| 19 | Remediation pipeline | golden path stubs | started |
| 20 | Verification | auth lab harness | partial |
| 21 | Adversarial integration | golden path | started |
| 22 | Counterexample loop | adversarial package | partial |
| 23 | Living twin | extended test | planned |
| 24 | Evidence pipeline | API events | partial |
| 25 | GhostLedger integration | seal in golden path | started |
| 26 | Bundle/replay | ghostledger | started |
| 27 | DB transactions | events store | planned |
| 28 | SSE stress | API tests | planned |
| 29 | Observability | trace IDs in golden path | started |
| 30 | Cost accounting | `GoldenPathBenchmark` | started |
| 31 | Multiverse UI | web + LIVE mode | planned |
| 32 | Execution UI | Director/Scheduler layers | planned |
| 33 | Evidence UI | provenance | planned |
| 34 | Frontend perf | stress fixture | planned |
| 35 | Accessibility | reduced motion | partial |
| 36 | Chaos | chaos matrix | planned |
| 37 | Security adversary | `M10_SECURITY_REVIEW.md` | planned |
| 38 | Benchmark integrity | `M10_END_TO_END_BENCHMARK.md` | planned |
| 39 | Release/cleanup | Makefile, OPERATIONS | started |
| 40 | Final reviewer | `M10_FINAL.md` GO/NO-GO | **NO-GO** (initial) |

## Golden path owner

**Lead + Agent 05/14/39** — only role authorized to consume live Vultr budget.
