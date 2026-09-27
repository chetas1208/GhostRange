# ADR-006: Vultr Integration Scope and RangeSpec-to-Instance Compilation

Status: Proposed (Agent 05, 2026-09-26). Depends on: Decisions.md #2, #4, #6, #7, #9. Feeds: `packages/vultr-control`, `packages/range-iac`, GhostScheduler design.
Full capability-by-capability evidence backing this ADR: `docs/research/VULTR.md` — read that first if you
want the FACT/OUR-INTERPRETATION breakdown per service; this ADR only restates what's needed to justify
the decision.

## Context

GhostRange reconstructs authorized infrastructure inside disposable "cyber worlds," lets agents
investigate incidents, forks competing remediation candidates into parallel worlds, adversarially
re-verifies them, and uses GhostScheduler to decide what compute runs where. Decisions.md already locked
Vultr as the IaaS target (via OpenTofu + cloud-init, #7) and left two things explicitly open for this
agent: (a) which Vultr services beyond bare Compute are actually worth integrating, and (b) VKE vs. plain
Compute for the worker fleet.

The project pitch claims Vultr is "architecturally fundamental" because its instance model (plan/OS/
image/SSH/startup-script/VPC/storage) maps cleanly onto an ephemeral-world architecture, and because its
compute portfolio (CPU, GPU, Kubernetes, serverless inference) spans what GhostRange needs. This ADR
verifies that claim against the actual Vultr API/provider schema (not marketing copy) and records where
the mapping is real versus where it's just available-but-unneeded.

## Decision

1. **Adopt now (M1):** Cloud Compute instances (range assets), the instance-template composition
   (os_id/snapshot_id + script_id/user_data + vpc_ids + firewall_group_id) as the RangeSpec compilation
   target, VPC 2.0 + Firewall Groups (per-world network isolation), Object Storage (evidence
   persistence), Managed Postgres (already locked by #6, pgvector available but unused), Managed Valkey
   (already locked by #4, now confirmed against real docs), and the Vultr API itself as the single
   integration surface behind `packages/vultr-control`.
2. **Defer, not reject:** VKE for the *orchestration/worker fleet* only, once M1 proves the loop and a
   real horizontal-scaling need shows up. Cloud GPU and Serverless Inference, only if a future milestone
   needs local/self-hosted model inference.
3. **Reject for M1:** VKE *for cyber-world assets* (wrong fidelity primitive — see below). Managed Kafka
   (Decisions.md #4/ADR-003 already rejected this for event transport on the merits; this ADR confirms
   that call against Vultr's real Kafka product docs rather than overriding it).
4. **Design constraint carried into GhostScheduler:** Vultr's API rate limit (~30 req/s per source IP)
   and documented snapshot-creation latency (20–30 minutes, not instant) mean GhostScheduler must not
   assume unlimited concurrent instance-create calls or instant fork-via-snapshot. All Vultr API access
   is centralized in `packages/vultr-control` so backoff/retry and any future request-queuing lives in
   exactly one place.

### Why instance templates are the right primitive for reproducible cyber worlds

**FACT vs OUR INTERPRETATION, kept explicit:** Vultr does not expose a single object literally called
"instance template." What it exposes (confirmed against the `vultr_instance` Terraform/Pulumi resource
schema, which mirrors the API v2 request body) is a **composable create-instance request** — a set of
independent fields that together fully describe a VM's initial state:

| Vultr create-instance field | What it controls | RangeSpec asset field it maps to (OUR INTERPRETATION) |
|---|---|---|
| `region` | Where the VM is physically provisioned | `asset.placement.region` (or world-level default) |
| `plan` | vCPU/RAM/disk size class | `asset.compute_class` (GhostScheduler-selected, cost/fidelity tradeoff) |
| `os_id` | Base OS image to boot from | `asset.base_image` when the asset is a *fresh* build |
| `snapshot_id` | Restore a prior snapshot instead of a bare OS | `asset.forked_from` when the asset is a *fork* of a previously-provisioned sibling (fast path for parallel-world creation) |
| `script_id` (startup script, base64, runs at boot) | One-shot boot-time commands, independent of cloud-init | `asset.role.boot_commands` — e.g. "start the vulnerable service" |
| `user_data` (cloud-init YAML, `#cloud-config`) | Declarative first-boot configuration (packages, files, users) | `asset.role.cloud_init_config` — the bulk of "what makes this asset behave like a domain controller / web server / jump box" |
| `vpc_ids` (list) | Which private VPC 2.0 network(s) this instance joins | `asset.network.vpc_membership` — derived from the RangeSpec's declared network topology, one VPC 2.0 per world (or per world+segment) |
| `firewall_group_id` | Stateful traffic filtering rules attached to the instance | Compiled from RangeSpec's declared reachability edges (`asset_a -> asset_b: port, protocol`) into `vultr_firewall_rule` entries |
| `ssh_key_ids` | SSH keys installed at boot | Operator/agent access keys, not part of the RangeSpec's *simulated* topology — an operational concern layered on top |
| `tags` / `label` / `hostname` | Identification metadata | `asset.id`, `asset.role.hostname` — used to correlate a live Vultr instance back to its RangeSpec asset for evidence/scheduler bookkeeping |
| `backups` / `backups_schedule` | Automated instance backups | Not used for range assets in M1 (assets are disposable by design; evidence, not instance backups, is the durability mechanism — see Object Storage in VULTR.md §7). Available if a future need for asset-level rollback emerges. |

The finding worth stating plainly: **this mapping is close to 1:1 because a RangeSpec asset is already,
by construction, "what boots, how it's configured, what it can talk to, how big it is" — which is exactly
the shape of Vultr's create-instance schema.** That's a genuine architectural fit, not just "Vultr has
enough features to make this work somehow." The one place it's *not* 1:1 is startup script vs.
cloud-init split — RangeSpec doesn't need two separate boot-config channels, so `packages/range-iac`'s
compiler design choice (OUR INTERPRETATION, not a Vultr requirement) is: **prefer `user_data`/cloud-init
for all declarative role configuration; reserve `script_id` startup scripts only for the narrow case of
commands that must run before cloud-init's full config is available** (cloud-init takes ~10 minutes to
finish processing per Vultr's own docs, so anything time-sensitive at boot may want the startup-script
path instead).

### Snapshots as the fork mechanism

"Fork competing remediation candidates into parallel worlds" needs forking to be *fast*. Vultr's snapshot
create-from-instance operation itself is documented as taking 20–30 minutes — not fast. The design
consequence (OUR INTERPRETATION): GhostRange should **pre-snapshot golden base images ahead of need**
(one snapshot per RangeSpec asset-role "template," built once, reused many times) so that the *fork* path
is always `snapshot_id -> new instance` (fast, an ordinary instance-create call), never
`instance -> new snapshot -> new instance` on the critical path of a fork request. This means
`packages/range-iac` needs two distinct compilation modes: "materialize a base world" (uses `os_id`,
ends by snapshotting each asset once it reaches steady state) and "fork a world" (uses each asset's
pre-existing `snapshot_id`, skips the OS-install/cloud-init-from-scratch path entirely). This is a design
choice this ADR is recording, not something the sponsor pitch's "templates" framing made obvious — it
only becomes visible once you check the actual snapshot-latency number.

### VPC 2.0 as the safety-boundary unit

Decisions.md #9 requires the safety boundary to be architectural, surviving a compromised/adversarial
agent — not just prompt-enforced. VPC 2.0's documented isolation guarantee ("VPC 2.0s are entirely
private, even from each other... your VPC 2.0s cannot pass traffic to each other") is a network-fabric-
level guarantee, independent of any agent's behavior inside a world. Design choice (OUR INTERPRETATION):
**one VPC 2.0 per world** (not per-investigation-with-shared-VPC), so that two forked worlds under
adversarial re-verification are isolated by the network fabric itself, not just by application-level
access control. Firewall Groups then express the *intended* topology inside a world (e.g. "the internet-
facing asset can be reached from anywhere, everything else only from inside the VPC"), compiled from the
RangeSpec's declared reachability edges.

## Alternatives considered

- **Containers/Kubernetes pods as range assets instead of VMs.** Rejected: breaks fidelity. A pod is not
  a believable stand-in for "a domain controller" the way a VM booted from a real OS image is, and
  CALDERA/Atomic-Red-Team-style tooling frequently assumes real OS/kernel behavior (raw sockets, registry,
  process trees) that containers only partially emulate. This is why VKE is REJECT for range assets
  specifically, even though it's a real, well-built product for GhostRange's *own* orchestration fleet.
- **Bare metal instead of Cloud Compute for range assets.** Rejected: provisioning latency and cost
  profile are wrong for disposable, short-lived, per-investigation worlds; Cloud Compute's hourly billing
  and fast create/terminate cycle fit the disposable-world model directly.
- **Config-management layer (Ansible/Salt) on top of bare instances instead of cloud-init/startup
  scripts.** Rejected per Decisions.md #7's existing rationale (OpenTofu + cloud-init already maps to
  RangeSpec compilation without an extra layer); this ADR's field-level mapping above is additional
  evidence that the simpler path is sufficient — the create-instance schema already carries everything a
  RangeSpec asset needs to express.
- **A single shared VPC across all worlds, with subnets or firewall rules for isolation instead of
  separate VPCs per world.** Considered, not chosen for M1: VPC 2.0's own documented lack of cross-VPC
  traffic gives a stronger, harder-to-misconfigure isolation guarantee than "trust the firewall rules were
  compiled correctly" within one shared network. Revisit if per-world VPC count becomes a real scaling
  constraint (each VPC 2.0 is region-scoped and does not support peering, so cross-region world designs
  would need reconsideration — flagged as NEEDS VERIFICATION on exact per-account VPC count limits in
  VULTR.md).
- **Vultr Managed Kafka instead of Valkey pub/sub for event transport.** Rejected — reaffirms
  Decisions.md #4/ADR-003. Verified against Vultr's actual Kafka product (real, well-documented, built
  for partitioned replay at higher operational cost) that it solves a different problem than M1's event
  fan-out needs. Not adopted just because Vultr offers it.
- **Vultr Serverless Inference or Cloud GPU as a required part of the M1 architecture.** Rejected for
  now — no locked M1 requirement needs self-hosted or Vultr-hosted model inference; including either would
  be sponsor-list padding rather than a real dependency. Recorded as viable future options in
  `docs/research/VULTR.md` §2–3.

## Consequences

- `packages/vultr-control` becomes the single, mockable choke point for all Vultr API calls (auth,
  instance/VPC/snapshot/firewall lifecycle, retry/backoff on 429). No other package calls the Vultr API
  directly. This also gives Decisions.md #9's safety boundary a natural enforcement point if
  range-ownership-token checks need to gate API calls.
- `packages/range-iac` needs two compilation modes (base-world materialization vs. snapshot-based fork),
  not one — this is new scope beyond "compile RangeSpec to OpenTofu" as a single flat operation, and
  should be reflected in that package's design (owned per Progress.md by the IaC Engineer / ADR-005).
- GhostScheduler's design must treat Vultr API throughput (~30 req/s per IP) and snapshot latency
  (20–30 min for a *new* snapshot; fast for restore-from-existing-snapshot) as real constraints, not
  assume infinite/instant parallelism when scoring how many worlds can be forked concurrently.
- VKE is explicitly out of scope for M1 code; the Progress.md open question ("VKE vs. plain Compute for
  worker fleet") is resolved as: plain Compute for M1, VKE candidate for the orchestration fleet only in
  a later milestone, never for range assets.
- Evidence durability now has an explicit Vultr-native answer (Object Storage) rather than being an open
  question dependent on Agent 12's hash-tree-vs-log decision alone — that decision determines *how*
  evidence is structured, not *whether* it needs to survive past instance/world teardown (it does, and
  Object Storage is where it lives).
- No live-credential Vultr integration exists yet anywhere in the codebase as of this ADR; all of the
  above is a design target for `packages/vultr-control`/`packages/range-iac`, validated in CI against
  mocked providers, with real-credential smoke tests explicitly gated/manual until API keys exist.
