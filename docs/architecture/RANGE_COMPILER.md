# GhostRange Range Compiler (M5)

## Pipeline

```
Authorized artifacts (Compose / TF / K8s / ghostrange.yaml)
        → parse → SourceModelV1
        → normalize → NormalizedSystemGraphV1
        → sanitize → SanitizedTwinGraph (in-memory + substitutions)
        → GhostIRV1
        → fidelity plan → FidelityProfileV1
        → TwinBlueprintV1
        → PlacementPlanV1
        → RangeSpecV2 + RangeTopologyPlan (range-iac)
        → VultrDeploymentPlanV1 → range-iac compile → provider apply
        → FidelityReportV1 + gates
        → GhostRange world READY
```

Package: `packages/range-compiler/` (`ghostrange_range_compiler`).

Existing `packages/range-iac` remains the **Vultr compilation target** for logical RangeSpec + topology — M5 feeds it, does not replace firewall/VPC logic.

## Safety

- Untrusted input — no blind provisioner execution  
- `SanitizationPolicyV1` default: reject plaintext secrets, stub externals, deny egress  
- UI/API never persist raw secret values  

## Fidelity

Question-relevant dimensions only (`FidelityProfileV1`).  
Investigation objective → rule-based profile mapping (policy); LLM may **suggest**, not authorize.

## GhostScheduler

`CompilationWorkloadV1` (future) schedules BUILD/PROVISION/VALIDATE tasks — separate from runtime task scheduling (M4).

## State machine

`CompilerState` in `twin_compiler.py`; emit `compiler.*` / `fidelity.*` domain events (Agent 19/events wave).

## Determinism

Content hashes at each stage; deterministic placement tie-break (sorted node ids).
