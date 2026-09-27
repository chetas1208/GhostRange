# World forking strategies — M3 research

**Question:** How does GhostRange fork one canonical base world into isolated remediation worlds on Vultr without mutating production and without fake parallel UI?

## Candidates

| Strategy | Startup latency | Cost | Fidelity | Isolation | Vultr fit | M3 complexity |
|----------|-----------------|------|----------|-----------|-----------|---------------|
| **A. Template + cloud-init replay** | Medium | Low | High (deterministic init) | VM-level | **Strong** — instance templates carry plan, image, SSH, user-data, VPC, storage | **Low** — extends M2 single-VM path |
| B. Provider snapshot clone | Low after snapshot exists | Medium (storage) | High if snapshot fresh | VM-level | Snapshots **20–30 min** to create — not on critical path (Decisions.md) | Medium |
| C. App/container snapshot + new infra | Medium | Medium | App-level | Container | Partial — compose on one VM today | High |
| D. Immutable image + init replay | Medium | Low | High | VM-level | Same as A if image pinned | Low |
| E. VM snapshot per fork | Low at fork time | Higher storage | Highest | VM-level | Requires pre-warmed golden snapshot | Medium |
| F. CoW filesystem | Low | Low | Depends | Process | Not first-class on Vultr | High |

## Measurements (M2 baseline)

- M2 auth-lab: **one physical VM**, four logical assets via Docker Compose (`topology.yaml`).
- `range-iac` already renders cloud-init + compose bundle per physical group.
- `RealVultrProvider.wait_until_ready` = API **active**, not cloud-init done — health probe still required (documented gap).

## Recommendation for M3

**Primary: Strategy A — fresh instance from same GhostRange template + deterministic cloud-init replay**, with:

- `WorldFingerprintV1` captured at base fork point (template id, scenario version, config hash).
- Per-child **distinct** `world_id`, VPC attachment or isolated network policy per ADR-M2 firewall rules.
- Optional **Strategy E** later: pre-warmed snapshot for fork latency once golden image exists (M4+).

**Defer:** Full Vultr **cluster** fleet for M3 unless scale-out worker pool proves cluster API reduces orchestration cost (see ADR-M3 §Clusters).

## Benchmark plan (Agent 23)

Compare fork strategies on:

- time_to_child_ready_ms  
- cost_per_child_usd  
- fingerprint match rate  
- teardown completeness  

Store under `artifacts/benchmarks/m3/fork-strategies/`.

## Sources

- Internal: `docs/adr/ADR-M2-RANGE-PROVISIONING.md`, `docs/research/VULTR.md`, `packages/vultr-control/README.md`
- Vultr product: instance templates (plan, OS/image, SSH, startup script, VPC, storage); cluster create-from-template (evaluate, do not assume)
