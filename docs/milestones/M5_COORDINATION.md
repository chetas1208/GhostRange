# M5 Coordination — Range Compiler + Fidelity Engine

**28 specialist workstreams** (prompt §76). Lead agent not counted.

## Contract freeze

**Wave 1:** `SourceModelV1`, `NormalizedSystemGraphV1`, `GhostIRV1`, `FidelityProfileV1`  
**Wave 4:** `TwinBlueprintV1`, `PlacementPlanV1`, `FidelityReportV1`, `CompilationManifestV1`, `RangeSpecV2`

## Agent table

| agent_id | mission | owned_paths | status | integration |
|----------|---------|-------------|--------|-------------|
| 01 | M5 audit | `docs/milestones/M5_AUDIT.md` | done | merged |
| 02 | Twin research | `docs/research/M5_RANGE_COMPILER_SYNTHESIS.md` | done | merged |
| 03 | Compiler architecture | `docs/architecture/RANGE_COMPILER.md` | done | merged |
| 04 | Source model | `packages/contracts/source/`, `source_model.py` | done | merged |
| 05 | System graph | `packages/contracts/system_graph/`, `system_graph.py` | done | merged |
| 06 | Ghost IR | `ghost_ir.py`, `range-compiler/.../ir/` | started | partial |
| 07 | Terraform HCL | `range-compiler/.../importers/terraform.py` | started | partial |
| 08 | Terraform plan JSON | `range-compiler/.../importers/tfplan.py` | planned | — |
| 09 | Compose | `range-compiler/.../importers/compose.py` | started | partial |
| 10 | Kubernetes | `range-compiler/.../importers/k8s.py` | started | partial |
| 11 | Multi-source merge | `range-compiler/.../merge/` | planned | — |
| 12 | Secret sanitization | `range-compiler/.../sanitize/secrets.py` | started | partial |
| 13 | Data replica | `range-compiler/.../sanitize/data.py` | planned | — |
| 14 | External deps | `range-compiler/.../sanitize/external.py` | planned | — |
| 15 | Network safety | `range-compiler/.../sanitize/network.py` | started | partial |
| 16 | Fidelity model | `fidelity_m5.py` | done | merged |
| 17 | Behavioral invariants | `range-compiler/.../fidelity/invariants.py` | planned | — |
| 18 | Fidelity validation | `range-compiler/.../fidelity/gates.py` | started | partial |
| 19 | Twin blueprint | `twin_compiler.py`, `compile/blueprint.py` | started | partial |
| 20 | Placement | `compile/placement.py` | started | partial |
| 21 | Vultr templates | `vultr-control` + template cache | planned | — |
| 22 | Snapshots benchmark | `artifacts/benchmarks/m5/snapshots/` | planned | — |
| 23 | Compiler runtime | `pipeline.py`, API hooks | started | partial |
| 24 | Multiverse UI | `apps/web` SourceShadow | planned | — |
| 25 | Execution/Evidence UI | compiler DAG + provenance | planned | — |
| 26 | Benchmark systems | `tests/fixtures/compiler/`, `artifacts/benchmarks/m5/` | started | partial |
| 27 | Adversarial input | security tests | planned | — |
| 28 | Integration gate | `M5_FINAL.md`, `M5_FIDELITY_REPORT.md` | planned | — |

## Waves

0: 01, 02 → 1: 03–06, 16 → 2: 07–11 → 3: 12–15 → 4: 17–23 → 5: 24–25 → 6: 26–27 → 7: 28

## Do-not-touch

- React #185 selector patterns (Agents 24–25, minimal edits)  
- Three primary tabs only  
- Raw secret persistence anywhere  
