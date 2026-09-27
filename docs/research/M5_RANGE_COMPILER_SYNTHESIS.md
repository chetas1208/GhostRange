# M5 Range Compiler Research Synthesis

Question-relevant fidelity — not perfect physical equivalence.

## SAFARI / Security-Investigation-as-Code

- **Problem:** Reproduce security investigations without touching production.  
- **Method:** Digital twins, Terraform, network virtualization, CALDERA-style replay in isolated replicas.  
- **GhostRange:** Aligns with **authorized IaC in → disposable twin out**, but M5 adds **multi-source normalization, explicit sanitization, fidelity dimensions, and evidence provenance**.  
- **Do not claim:** GhostRange implements CALDERA or full SAFARI stack verbatim.

## Cybersecurity digital twin surveys (2024–2026)

- **Problem:** Twins vary in fidelity; validation often assumed.  
- **Method:** Architecture layers (data, model, service, network) + validation loops.  
- **GhostRange:** `FidelityProfileV1` per investigation objective; `FidelityReportV1` per dimension; **gates before strong claims**.  
- **Do not claim:** Survey “95% fidelity” language maps to our scores without defined metrics.

## Quantitative security-twin validation

- **Problem:** Structural similarity ≠ behavioral equivalence.  
- **Method:** Invariant tests, observed vs twin comparison.  
- **GhostRange:** `BehavioralInvariantV1`, `InvariantComparisonV1`, mutation tests (Agent 18/26).  
- **Do not claim:** Passing topology checks implies production transferability.

## Cyber-range scenario generation / federation

- **Problem:** Manual range authoring does not scale.  
- **Method:** Scenario templates, federation protocols, reproducibility metadata.  
- **GhostRange:** `CompilationManifestV1`, deterministic fingerprints, blueprint revisions.  
- **Do not claim:** Federation with external ranges in M5.

## IaC replication pitfalls

- **Problem:** Terraform/Compose/K8s express different abstractions.  
- **Method:** Normalized graph intermediate representation.  
- **GhostRange:** `NormalizedSystemGraphV1` → `GhostIRV1` → `TwinBlueprintV1`.  
- **Do not claim:** Full HCL/K8s feature coverage in M5 v1.

## Vultr-specific (product, not papers)

- **Instance templates:** plan, OS, SSH, startup, VPC, storage, cloud-init — reuse via `TemplateFingerprintV1`.  
- **Snapshots:** disk clone; creation latency scales with size — **benchmark before defaulting** (Agent 22).  
- **Terraform provider:** declarative lifecycle — output `VultrDeploymentPlanV1`, not raw `terraform apply` on user production.

## M5 research questions (RQ1–RQ6)

| RQ | M5 artifact |
|----|-------------|
| RQ1 normalize heterogeneous inputs | System graph + merge engine |
| RQ2 fidelity required for meaning | FidelityProfile + gates |
| RQ3 auto-identify preserved properties | Rule-based objective → profile (policy, not LLM-only) |
| RQ4 sensitive state replacement | Sanitization + DataReplicaPolicy |
| RQ5 measure reconstruction | FidelityReport + invariants |
| RQ6 behavioral invariants | Twin validation runtime |

## Rejected for M5

- LLM-only compilation  
- Blind production cloning  
- Single “fidelity percentage” marketing metric  
- VKE by default for every K8s import  
