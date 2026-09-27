# Vultr Platform Research — GhostRange (Agent 05)

Status: research complete, feeds ADR-006. Owner: Agent 05 (Vultr Infrastructure Researcher).
Scope: verify, capability by capability, whether the claim "Vultr is architecturally fundamental to
GhostRange" holds up, using current Vultr documentation rather than the sponsor pitch.

**Convention used throughout:** every subsection separates **FACT** (what Vultr's own docs/API state,
with source links) from **OUR INTERPRETATION** (how GhostRange chooses to use that fact — a design
choice, not something Vultr requires). Anything I could not pin to a primary Vultr doc, or that looked
like it might have changed recently, is flagged **NEEDS VERIFICATION**.

Knowledge basis: live web search/fetch against docs.vultr.com, vultr.com, the Terraform/Pulumi provider
docs (which mirror the Vultr API v2 schema), and cloud-init's own Vultr datasource docs, run 2026-09-26.
Vultr ships product changes frequently (their own VKE changelog is evidence of this cadence) — treat
exact field names as accurate as of this date and re-verify against `docs.vultr.com` before hackathon
demo day if this doc is more than a few weeks old.

---

## 1. Vultr Cloud Compute (CPU instances, plans)

**FACT:** Vultr Cloud Compute splits into Shared CPU (general purpose) and Dedicated/High-Frequency/
Optimized CPU (consistent performance, production workloads) lines, plus a newer VX1 line with plans
from 2–192 vCPUs. Entry plans start around $2.50–3.50/mo (1 vCPU / 512MB); pricing scales up through the
thousands/month for the largest VX1 shapes. Billing is hourly, capped at a monthly rate, with optional
reserved/committed pricing for 1–3 year terms.
[Vultr VX1](https://www.vultr.com/products/vx1-compute/), [Vultr pricing](https://www.vultr.com/pricing/)

**OUR INTERPRETATION:** This is the baseline substrate for a "cyber world" — every reconstructed
authorized-infrastructure asset (a domain controller stand-in, a web server, a jump box) is a Cloud
Compute instance. Cheap per-hour entry plans matter directly for cost control: a GhostRange world with
N assets running for the duration of one investigation is bounded and disposable, so we want the
smallest viable plan per asset role, selected by GhostScheduler, not a fixed "one size" template.

```
WHY IT EXISTS
Vultr's core IaaS product: on-demand, hourly-billed virtual machines across a global region footprint.

WHAT PRODUCT REQUIREMENT IT SATISFIES
"Reconstruct authorized infrastructure inside disposable environments" requires a compute primitive
that can be created and destroyed in seconds-to-minutes, per range, per fork. This is that primitive.

WHAT WOULD BREAK/CHANGE WITHOUT IT
Without a fast, API-driven VM primitive, GhostRange would have to target bare metal (too slow to
provision, wrong cost profile) or a container-only model (breaks fidelity for ranges that need to
emulate a real OS/kernel, e.g. Windows AD behavior, raw socket tooling used by CALDERA/Atomic Red Team).

HOW IT APPEARS IN THE ARCHITECTURE
`packages/vultr-control` wraps instance create/list/terminate; `packages/range-iac` compiles a
RangeSpec asset entry into an OpenTofu `vultr_instance` resource with plan/region/os_id chosen by
GhostScheduler's cost/fidelity tradeoff (see ADR-006 §RangeSpec compilation).

HOW IT WILL BE TESTED
Integration test: compile a 2-asset synthetic RangeSpec, `tofu plan` against a mocked Vultr provider
(no live credentials in CI), assert the generated instance resources have the expected plan/region/
os_id. A live-credential smoke test (manual, gated behind an env var) provisions and immediately
terminates one instance to confirm end-to-end reachability once real API keys exist.
```

---

## 2. Vultr Cloud GPU instances

**FACT:** Vultr offers Cloud GPU instances spanning NVIDIA A100 (PCIe and HGX), H100 (primarily sold as
an 8×HGX H100 80GB bare-metal chassis, ~$23.92/hr for the full chassis, ≈$2.99/GPU-hr), L40S, A40, A16,
GH200, with early-access HGX B200 and (as of a Dec-2025 announcement — **NEEDS VERIFICATION**, this is
right at my knowledge boundary) preemptible AMD MI325X/MI355X plans. Reserved 12-month terms offer
~30% discount; on-demand is hourly, no minimum commitment.
[Vultr Cloud GPU](https://www.vultr.com/products/cloud-gpu/), [pricing analysis](https://www.spheron.network/blog/vultr-cloud-gpu-pricing-2026/)

**OUR INTERPRETATION:** GPU instances are relevant to GhostRange in exactly one place: if an
investigating/remediation agent itself needs local GPU inference (e.g. running an open-weight model for
log analysis at scale, or training/fine-tuning a detector inside a world for research purposes). They
are **not** needed to run the cyber-range assets themselves — those are ordinary CPU workloads.

```
WHY IT EXISTS
Vultr's answer to on-demand ML training/inference infrastructure, competing on GPU availability and
per-GPU-hour pricing against hyperscalers.

WHAT PRODUCT REQUIREMENT IT SATISFIES
Optional: local/offline model inference or fine-tuning as part of an investigation workflow, if a
milestone needs it (not required for M1; GhostRange's default LLM calls go through the orchestration
layer, not a self-hosted GPU box).

WHAT WOULD BREAK/CHANGE WITHOUT IT
Nothing in the core loop (world creation, investigation, forking, adversarial re-verification,
scheduling) requires a GPU. Losing this would only remove an optional self-hosted-inference path.

HOW IT APPEARS IN THE ARCHITECTURE
Not in M1. If adopted later, it would be a GhostScheduler-selectable "compute class" for a narrow set
of agent tasks (e.g. a bulk-log-embedding job), never for range assets.

HOW IT WILL BE TESTED
N/A for M1 — no code path exercises this.
```

**Verdict: DEFER, not REJECT.** GPU instances are real and well-documented, but GhostRange's M1 loop has
no workload that needs one. Re-evaluate if a later milestone adds local model hosting; until then this
is not "architecturally fundamental," it's an available option we are choosing not to use yet.

---

## 3. Vultr Serverless Inference

**FACT:** Vultr Serverless Inference is a managed, OpenAI-compatible REST API for LLM chat completions
(`https://api.vultrinference.com/v1/chat/completions`) plus a vector-store endpoint
(`https://api.vultrinference.com/v1/vector_store`) for RAG-style workflows, authenticated with a Vultr
API key. [Vultr Serverless Inference docs](https://docs.vultr.com/products/serverless/inference)

**OUR INTERPRETATION:** This is a genuine alternative to standing up our own GPU box for inference, and
its OpenAI-compatible surface means it's a drop-in for any agent component that expects an
OpenAI-shaped client. Still not core to the M1 loop (the project's LLM orchestration is not locked to a
specific inference provider in Decisions.md), but worth flagging as the lower-friction path if/when
GhostRange wants Vultr-hosted inference instead of self-managed GPU instances, and it removes the need
for #2 (Cloud GPU) in that scenario entirely.

```
WHY IT EXISTS
Vultr's managed, pay-per-token LLM hosting product — avoids customers managing GPU instances directly
for standard chat/embedding workloads.

WHAT PRODUCT REQUIREMENT IT SATISFIES
None in M1's locked scope. Candidate for a later milestone that wants Vultr-native inference instead of
an external LLM API, keeping the whole stack (compute, network, model calls) inside one provider for a
cleaner "everything about this cyber-world lives on Vultr" story.

WHAT WOULD BREAK/CHANGE WITHOUT IT
Nothing breaks — it's additive optionality, not a dependency.

HOW IT APPEARS IN THE ARCHITECTURE
Not wired in M1. If adopted, it would sit behind whatever LLM client abstraction the orchestration
packages already use, as one more backend, not a special case.

HOW IT WILL BE TESTED
N/A for M1.
```

**Verdict: DEFER.** Real capability, OpenAI-compatible, low integration cost if ever needed — but there
is no locked M1 requirement pulling it in, so including it now would be padding.

---

## 4. Vultr instance templates / snapshots / cloud-init / startup scripts

This is the capability the sponsor pitch leans on hardest, so it gets the most scrutiny. I fetched the
actual Terraform/Pulumi provider schema (which mirrors the Vultr API v2 request body 1:1) to get exact
field names rather than relying on marketing copy.

**FACT — instance creation fields** (from the `vultr_instance` Terraform resource / Pulumi `vultr.Instance`,
both generated from the same Vultr API v2 schema):
required: `region`, `plan`. Optional, relevant to GhostRange: `os_id`, `iso_id`, `app_id`, `image_id`
(marketplace app), `snapshot_id` (restore from a snapshot instead of a bare OS), `script_id` (attach a
startup script), `ipxe_chain_url`, `firewall_group_id`, `vpc_ids` (list — attach to one or more VPC 2.0
networks), `vpc_only` (no public IP, VPC-only, requires a NAT gateway), `ssh_key_ids`, `user_data`
(cloud-init config, consumed on first boot), `backups` + `backups_schedule`, `enable_ipv6`,
`disable_public_ipv4`, `ddos_protection`, `hostname`, `label`, `tags`, `reserved_ip_id`,
`app_variables`, `block_devices` (for VX1 storage config).
[Terraform vultr_instance docs](https://registry.terraform.io/providers/vultr/vultr/latest/docs/resources/instance)

**FACT — snapshots:** `vultr_snapshot` takes `instance_id` (required, source instance) and `description`
(optional); creation is a live-instance-to-image operation that Vultr's own docs say can take 20–30
minutes depending on instance size. A snapshot's ID can then be passed back into `snapshot_id` on a new
instance create call to restore it. [Vultr snapshot docs](https://docs.vultr.com/products/orchestration/snapshots/provisioning)

**FACT — startup scripts:** `vultr_startup_script` takes `name` (required), `script` (required, base64-
encoded), and `type` (`boot` or `pxe`, default `boot`). These run once at instance boot, independent of
cloud-init. [Vultr startup script docs](https://docs.vultr.com/products/orchestration/startup-scripts/provisioning)

**FACT — cloud-init:** Vultr instances accept a `user-data` cloud-config (YAML, `#cloud-config` shebang)
that cloud-init processes on first boot; Vultr's own docs note this takes roughly 10 minutes to complete
after instance creation. cloud-init has a first-class Vultr datasource that reads config from the local
metadata service. [Vultr + Terraform + cloud-init guide](https://docs.vultr.com/products/provision-a-vultr-cloud-server-with-terraform-and-cloud-init),
[cloud-init Vultr datasource](https://docs.cloud-init.io/en/latest/reference/datasources/vultr.html)

**FACT — metadata service:** every Vultr instance can query itself, unauthenticated, over HTTP at
`169.254.169.254` (`/v1/` root), returning instance ID, region, plan, network config, and the user-data
that was supplied at creation. No credentials needed since it's link-local.
[Vultr metadata docs](https://www.vultr.com/metadata/)

**OUR INTERPRETATION:** This is the actual load-bearing claim, and it holds up as stated but needs a
precise framing: **there is no single Vultr object called "instance template."** What Vultr actually
gives you is a *composable create-instance request* — `os_id`/`snapshot_id`/`image_id` (what boots),
`script_id` + `user_data` (how it's configured after boot), `vpc_ids` + `firewall_group_id` (what it can
talk to), `plan`/`region` (where and how big). A RangeSpec asset definition maps cleanly onto exactly
this tuple, field for field — that's the real finding, and it's stronger than "Vultr has templates," it's
"Vultr's create-instance schema is already shaped like a declarative asset spec." Concrete field mapping
is spelled out in ADR-006. Snapshots are the mechanism for "golden image" reuse across forked worlds
(build once, restore into N forked instances instead of re-running provisioning N times) — this matters
directly for the "fork competing remediation candidates into parallel worlds" requirement, because
forking should be cheap and fast, and restoring a snapshot is much faster than re-provisioning from a
bare OS + cloud-init + startup script each time.

```
WHY IT EXISTS
Vultr's create-instance API is a single declarative request that fully specifies a VM's initial state
(image, config-on-boot, network membership, size) so it can be automated without console interaction.
Snapshots exist so that state can be captured once and replayed cheaply.

WHAT PRODUCT REQUIREMENT IT SATISFIES
"RangeSpec compiles to reproducible infrastructure" and "forking a world should be fast" are both
requirements this satisfies directly: RangeSpec asset fields map onto create-instance fields (see
ADR-006), and snapshot-restore is the fast path for cloning an asset into a forked world instead of
replaying full provisioning.

WHAT WOULD BREAK/CHANGE WITHOUT IT
Without a declarative, API-driven create-with-config primitive, "compile a RangeSpec into infrastructure"
would require either hand-configuring VMs after boot (slow, not reproducible, breaks the disposable-
world model) or a heavier config-management layer (Ansible/Salt) bolted on top — which OpenTofu +
cloud-init already avoids per Decisions.md #7. Without snapshots specifically, forking N parallel worlds
means re-running full provisioning N times, which directly hurts the "many parallel forks, adversarially
re-verified" performance goal.

HOW IT APPEARS IN THE ARCHITECTURE
`packages/range-iac` compiles each RangeSpec asset into an OpenTofu resource block using `os_id` (base
build) or `snapshot_id` (fork restore), `script_id`/`user_data` (role config — e.g. "this asset is a
vulnerable web server, install and configure nginx + the vulnerable app version"), `vpc_ids` (segment
membership), `firewall_group_id` (intra-range traffic policy). Forking a world = snapshot the base
instance(s) once, then compile N sibling worlds' RangeSpecs against `snapshot_id` instead of `os_id`.

HOW IT WILL BE TESTED
Unit test on the RangeSpec→OpenTofu compiler: given a fixture RangeSpec with 2 assets (one from a base
OS, one marked "fork of asset X"), assert the emitted `vultr_instance` blocks use `os_id` for the first
and `snapshot_id` for the second, and that `user_data`/`script_id` are populated from the asset's role
config. No live Vultr calls in this test — it's a pure compiler test against a mocked provider schema.
A separate manual/gated smoke test (once credentials exist) provisions one real instance from a real
snapshot and confirms boot + cloud-init completion via the metadata service.
```

---

## 5. Vultr VPC / network isolation

**FACT:** Vultr VPC 2.0 provides a private, region-scoped L2 network that instances attach to via
`vpc_ids` at creation or afterward. `vultr_vpc2` (Terraform) takes `region`, `description`, `v4_subnet`,
`v4_subnet_mask`. VPC 2.0 networks are private even from each other — other customers cannot observe
traffic, and separate VPC 2.0 networks cannot pass traffic to each other. Documented limitations: no VPC
peering, cannot span regions, no broadcast/multicast, no DHCP (static addressing expected).
[VPC 2.0 docs](https://docs.vultr.com/products/network/vpc-2), [vultr_vpc2 resource](https://registry.terraform.io/providers/vultr/vultr/latest/docs/resources/vpc2)
There is also a separate, older/simpler `vultr_vpc` resource ("VPC" — non-"2.0") and Vultr's own docs
include a migration guide from the older VPC to VPC 2.0, implying VPC 2.0 is the current recommended
generation. **NEEDS VERIFICATION**: whether the original "VPC" (gen 1) is still provisionable for new
accounts or is legacy-only as of this date.

Separately, **Firewall Groups** (`vultr_firewall_group` + `vultr_firewall_rule`) provide stateful,
rule-based filtering (`ip_type`, `protocol`, `port`, `source`) attached to instances via
`firewall_group_id`, independent of VPC membership. [Firewall docs](https://docs.vultr.com/products/network/firewall-groups)

**OUR INTERPRETATION:** VPC 2.0 is the direct mechanism for "network isolation between cyber worlds" —
each RangeSpec-derived world gets its own VPC 2.0 network (or a private subnet within one), so that two
forked worlds investigating the same incident cannot see or interfere with each other's traffic, and a
compromised/adversarial agent inside one world cannot pivot laterally into a sibling world's assets over
the network layer. Firewall Groups are the finer-grained control *within* a world — e.g. restricting an
"internet-facing" asset's egress or enforcing the intended attack-path topology (this maps to
Decisions.md #9's requirement that the safety boundary be architectural, not prompt-based: a VPC boundary
plus firewall rules is enforced by the network fabric, not by agent behavior).

```
WHY IT EXISTS
Isolated private networking so cloud tenants can build multi-tier topologies without exposing internal
traffic to the public internet or other tenants.

WHAT PRODUCT REQUIREMENT IT SATISFIES
Directly satisfies "the safety boundary must survive a compromised or adversarial agent" (Decisions.md
#9) at the network layer, and "fork competing remediation candidates into parallel worlds" requires that
forks not cross-contaminate — VPC-per-world is the isolation unit.

WHAT WOULD BREAK/CHANGE WITHOUT IT
Without VPC isolation, every asset would need a public IP + host-level firewalling only, which is weaker
(relies on every instance being correctly configured, no network-fabric-level guarantee) and would make
"parallel forked worlds" riskier — a bug in one world's asset config could expose it to, or attack,
another world's assets on the shared public internet surface.

HOW IT APPEARS IN THE ARCHITECTURE
`packages/range-iac` provisions one `vultr_vpc2` per RangeSpec-derived world (or reuses one per
investigation with per-world subnets — open design question, see ADR-006 alternatives), attaches every
asset instance's `vpc_ids` to it, and compiles RangeSpec-declared "reachability" edges into
`vultr_firewall_rule` entries scoped to a `firewall_group_id` per asset role.

HOW IT WILL BE TESTED
Compiler test: fixture RangeSpec declaring two assets with an explicit "A can reach B on 443, nothing
else" edge → assert the compiled OpenTofu includes one VPC, both instances attached to it, and firewall
rules that allow exactly that edge and nothing broader. A live network test (manual, gated) provisions
two real instances in the same VPC 2.0 and confirms private connectivity + confirms a second VPC 2.0
cannot reach either, matching Vultr's documented "VPC 2.0s cannot pass traffic to each other" behavior.
```

---

## 6. Vultr Kubernetes Engine (VKE)

**FACT:** VKE is a managed Kubernetes service — Vultr runs the control plane (free), customer pays for
worker nodes, load balancers, block storage. Supports multiple node pools per cluster with different
compute types (mixed CPU/GPU pools), manual or autoscaled node pools, a Vultr Cloud Controller Manager
(assigns node IPs, deploys managed load balancers automatically) and a Vultr CSI driver for block storage,
deployed by default. [VKE docs](https://docs.vultr.com/support/products/vke/what-is-kubernetes-and-vultr-kubernetes-engine)

**OUR INTERPRETATION:** This was flagged in Decisions.md as an open question ("VKE vs. plain Compute
instances for worker fleet — owned by Agent 05"). My conclusion: **VKE is the right fit for the
GhostRange *control plane/worker fleet* (the thing that runs range-runtime, scheduler, evidence services,
CALDERA adapter, API) but the wrong fit for the *cyber-world assets themselves***, and these are two
separate compute populations that should not be conflated:

- **Orchestration/worker fleet** (stateless-ish services: API, scheduler, range-runtime workers that
  drive Vultr API calls, evidence collectors): benefits from VKE's autoscaling node pools and managed
  load balancing as the number of concurrent investigations grows. This is the "GhostScheduler decides
  what compute runs where" layer, and it wants elastic capacity, not a fixed VM per component.
- **Cyber-world assets** (the reconstructed domain controller, web server, etc. that CALDERA/agents
  attack and defend): these need to *look like* real standalone hosts with real OS-level behavior,
  network identity, and boot semantics that RangeSpec/cloud-init directly targets. Running them as
  Kubernetes pods would fight the fidelity requirement (a pod is not a believable stand-in for "a
  domain controller" the way a VM booted from a Windows/Linux image is) and would duplicate the
  templating story that Vultr Instances + snapshots + cloud-init already solve cleanly (§4).

So: plain Cloud Compute instances for range assets (locked), VKE as a **candidate** for the orchestration
fleet once M1's "does the repo boot" bar is cleared and there's an actual multi-worker scaling need —
not required for M1, where a small number of long-lived Compute instances (or even a single dev box) is
sufficient and simpler to debug.

```
WHY IT EXISTS
Vultr's managed container-orchestration product, so customers don't operate their own control plane.

WHAT PRODUCT REQUIREMENT IT SATISFIES
Elastic scaling of GhostRange's own orchestration services (API, scheduler, workers) as concurrent
investigation/fork count grows — NOT the cyber-world assets.

WHAT WOULD BREAK/CHANGE WITHOUT IT
Nothing breaks for M1. Without it later, the orchestration fleet would need manually managed Compute
instances behind a hand-rolled load balancer — more ops burden as concurrency grows, but not a blocker.

HOW IT APPEARS IN THE ARCHITECTURE
Not in M1 (locked stack runs orchestration as plain services; local/dev deploy target). Candidate for
M2+: `packages/range-runtime` workers and `apps/api` become a VKE-deployed node pool once horizontal
scaling is actually needed; range *assets* remain plain `vultr_instance` resources regardless.

HOW IT WILL BE TESTED
N/A for M1 — no VKE code path exists yet. When adopted, test via a standard k8s deployment manifest +
`kubectl get pods` health check in CI against a disposable VKE cluster (or kind/minikube locally for
manifest correctness without live Vultr spend).
```

**Verdict at time of original research: DEFER for the orchestration fleet (real candidate, not needed
yet), REJECT for cyber-world assets specifically** (wrong primitive for the fidelity requirement — Cloud
Compute + snapshots/cloud-init is correct there, see §4).

### 2026-09-27 update — DEFER promoted to ADOPT (design), real cluster still not created

The "M1's does the repo boot bar is cleared" condition this section originally deferred behind has now
passed for the control-plane services specifically (`api`, `web`, `valkey`, the `caddy` reverse proxy —
all four already run in production today per `docker-compose.prod.yml` on a single Compute VM). This
update **does not** relitigate the range-asset REJECT above — that stands unchanged, verified again against
ADR-006 and Decisions.md #11 before starting this work. It narrows and acts on the orchestration-fleet
DEFER only.

**What changed:** a full, real Kubernetes manifest set for the control plane now exists at `deploy/k8s/`
(Kustomize base + `vke`/`local-kind` overlays — plain manifests, not Helm, since this repo has zero Helm
usage anywhere and Valkey's config has no persistence to justify a StatefulSet/Bitnami subchart). Full
reasoning for every design choice (Postgres/Object Storage staying external, Valkey as a plain Deployment,
Caddy as the ingress instead of installing ingress-nginx) is in `docs/deployment/VKE_DEPLOY.md`, which is
also the exact-command runbook for actually creating a cluster and deploying to it.

**What was validated, and how (real commands, not claimed):** `kustomize build` rendered all three
variants (base, vke overlay, local-kind overlay) with no errors, 11 resources each; `kubeconform -strict`
validated all three renders against the real Kubernetes 1.30 OpenAPI schema — `Valid: 11, Invalid: 0,
Errors: 0` for every variant. A real local cluster (`kind`, then `k3d`) was attempted as the strongest
possible proof (actual pod scheduling, not just schema validity) and both failed for the same underlying
reason: this sandbox's Docker is rootless with no systemd user session, so neither tool can get the cgroup
delegation they require. That is a sandbox limitation, not a manifest defect — see
`docs/deployment/VKE_DEPLOY.md`'s "Local validation performed" section for the exact error output and root
cause. **No real VKE cluster was created** — that is a new billable resource explicitly held for the user's
go-ahead, consistent with how this session has treated every other live-spend decision today.

**Verdict, updated: ADOPT for the orchestration/control-plane fleet at the design/manifest level; REAL
CLUSTER CREATION deliberately NOT_RUN pending approval.** REJECT for cyber-world assets is unchanged. This directly resolves the Decisions.md open question.

---

## 7. Vultr Object Storage

**FACT:** S3-compatible (subset of the S3 API — Vultr publishes a compatibility matrix; not full parity),
region-scoped endpoints (e.g. `ewr1.vultrobjects.com` for New Jersey), usable via any S3 SDK/tool
(`s3cmd`, S3 Browser, boto3-style clients pointed at the custom endpoint).
[Object Storage docs](https://docs.vultr.com/products/storage/object-storage), [S3 compatibility matrix](https://docs.vultr.com/products/cloud-storage/object-storage/s3-compatibility-matrix)

**OUR INTERPRETATION:** Good fit for evidence artifact storage — Agent 12's evidence/provenance package
needs durable, content-addressable-friendly blob storage for collected artifacts (logs, memory dumps,
CALDERA execution transcripts) that outlive the disposable world that produced them. S3-compatibility
means the evidence package can use a standard S3 client library rather than a bespoke Vultr SDK, which is
good for testability (mock with any local S3-compatible test double, e.g. minio, in CI).

```
WHY IT EXISTS
Vultr's durable blob storage product, S3-API-compatible so existing S3 tooling/clients work unmodified.

WHAT PRODUCT REQUIREMENT IT SATISFIES
Evidence must persist after the disposable world that generated it is destroyed — this is the storage
tier for that. Also a natural home for OpenTofu state files and instance snapshots' associated metadata
if not using Vultr's own snapshot storage exclusively.

WHAT WOULD BREAK/CHANGE WITHOUT IT
Without durable off-instance storage, evidence would either need to live on the range-runtime's own
Postgres (fine for structured metadata, wrong for large blobs like memory dumps or pcap captures) or be
lost when the world is torn down — directly breaking the "adversarially re-verified" and audit-trail
goals, which need evidence to survive past the world's lifetime.

HOW IT APPEARS IN THE ARCHITECTURE
`packages/evidence` writes large artifacts to an Object Storage bucket (one per investigation or
content-addressed globally, per Agent 12's hash-tree-vs-log decision) via a standard S3 client;
Postgres holds metadata/pointers, not the blobs themselves.

HOW IT WILL BE TESTED
Evidence package tests run against a local S3-compatible test double (e.g. minio in a test container or
an in-memory fake implementing the same client interface) — no live Vultr credentials needed for CI.
A gated manual test confirms a real upload/download round-trip against a real Object Storage bucket.
```

**Verdict: ADOPT** for evidence/artifact persistence. Genuinely useful, not sponsor-list padding — the
evidence-survives-the-world requirement needs blob storage somewhere, and this is the natural Vultr-native
answer given everything else is already on Vultr.

---

## 8. Vultr Managed Databases — PostgreSQL, pgvector

**FACT:** Vultr Managed Database for PostgreSQL supports common extensions including `pgvector`,
PostGIS, `pg_stat_statements`, `hstore`, enabled via console or CLI without custom compilation. HA is via
automated health checks + leader election + replica promotion; read-only replicas can be added in other
Vultr regions; automated daily backups with point-in-time recovery (WAL-based) on all non-Hobbyist plans.
[pgvector/PostGIS blog](https://blogs.vultr.com/PG-Vector-PostGIS), [Managed DB HA](https://docs.vultr.com/support/products/managed-databases/how-is-high-availability-achieved-in-a-vultr-managed-database)

**OUR INTERPRETATION:** Decisions.md #6 already locks Postgres as the DB, specifically to avoid
SQLite/Postgres drift versus "Vultr Managed Postgres from day one" — so this section mostly confirms that
decision is well-founded rather than introducing something new. The pgvector finding is the interesting
addition: if GhostRange ever wants semantic search over evidence (e.g. "find prior incidents similar to
this one" or embedding-based retrieval for an investigating agent), pgvector-on-Managed-Postgres means
that capability is a schema/extension change, not a new infrastructure dependency (no separate vector DB
needed).

```
WHY IT EXISTS
Vultr's managed relational database offering, positioned as a drop-in for self-hosted Postgres with HA/
backup/patching handled by Vultr.

WHAT PRODUCT REQUIREMENT IT SATISFIES
Decisions.md #6's requirement directly (schema parity from day one). pgvector specifically would satisfy
a future "semantic evidence retrieval" requirement if one is adopted, without adding a new DB technology.

WHAT WOULD BREAK/CHANGE WITHOUT IT
Without Managed Postgres, the team runs and patches its own Postgres, which Decisions.md already
rejected as a distraction. Without pgvector specifically, semantic search over evidence would need a
dedicated vector store (e.g. a hosted vector DB) — an extra moving part with its own ops/cost, currently
unjustified since no milestone has locked a semantic-retrieval requirement yet.

HOW IT APPEARS IN THE ARCHITECTURE
Local/dev uses containerized Postgres (per Decisions.md #6); the same schema targets Vultr Managed
Postgres for staging/prod. `packages/contracts` models (RangeSpecV1, EvidenceV1, SchedulerDecisionV1)
persist here. pgvector is not enabled by default in M1 — it's a documented option, not a dependency,
until a retrieval use case is actually adopted.

HOW IT WILL BE TESTED
Already covered by Decisions.md #6's own rationale: CI runs the real schema against containerized
Postgres so dialect behavior matches Managed Postgres; no SQLite anywhere in the test matrix. If
pgvector is adopted later, its tests would run against a containerized Postgres image with the
extension installed, mirroring what Managed Postgres offers.
```

**Verdict: ADOPT (already locked via Decisions.md #6); pgvector = DEFER** (real, documented, zero-cost
optionality — not needed until a retrieval requirement exists).

---

## 9. Valkey/Redis-compatible managed offering

**FACT:** Vultr Managed Databases for Valkey — a Redis-compatible in-memory data store, deployed across
33 global regions, supporting pub/sub, streams, sorted sets, with HA and automated backups.
[Valkey docs](https://docs.vultr.com/products/storage/databases/valkey)

**OUR INTERPRETATION:** Decisions.md #4 already locks "Redis/Valkey pub-sub for local + M1 (matches
future Vultr-managed Valkey)" — this research confirms that Vultr's managed Valkey product genuinely
supports the pub/sub + streams pattern the event-transport decision assumes, so the "matches future
Vultr-managed Valkey" clause in Decisions.md is verified, not aspirational.

```
WHY IT EXISTS
Vultr's managed in-memory store, positioned as a drop-in Redis-compatible service for caching,
messaging, and real-time data patterns without self-hosting Redis/Valkey.

WHAT PRODUCT REQUIREMENT IT SATISFIES
Decisions.md #4's event-transport decision directly: cheap, low-latency pub/sub for range-runtime event
propagation to the scheduler and UI-facing event stream, with a managed upgrade path already confirmed
to exist.

WHAT WOULD BREAK/CHANGE WITHOUT IT
Without a managed path, local Valkey/Redis would need self-hosting in staging/prod too, adding ops
burden Decisions.md #4 explicitly wanted to avoid by choosing something "already a planned Vultr-native
dependency."

HOW IT APPEARS IN THE ARCHITECTURE
`packages/events` uses Redis/Valkey pub-sub locally (containerized) and targets Vultr Managed Valkey for
non-local environments — same protocol, so no client-code branching needed.

HOW IT WILL BE TESTED
Already covered by the existing events package test plan (owned by Agent 15): pub/sub integration tests
run against a local Valkey/Redis container; protocol compatibility means no separate Vultr-specific test
path is needed beyond a connection-string swap.
```

**Verdict: ADOPT (already locked via Decisions.md #4, now independently confirmed against real Vultr
docs).**

---

## 10. Vultr Kafka / event streaming

**FACT:** Vultr Managed Apache Kafka exists — a managed Kafka service across all Vultr regions, with an
expanding set of Kafka Connect connectors (MongoDB, Snowflake, BigQuery, etc.), positioned for
high-throughput real-time data pipelines, and documented as integrable with Vultr Serverless Inference
for streaming AI pipelines. [Managed Kafka docs](https://docs.vultr.com/products/managed-database/kafka)

**OUR INTERPRETATION — REJECT for GhostRange's event transport.** This is a real, well-documented Vultr
product, but it does not fit here, and Decisions.md #4 already made this call for the right reason: M1's
event volume doesn't need replay/partitioning semantics, and Redis/Valkey pub-sub is simpler, cheaper,
and already the locked choice with a confirmed managed upgrade path (§9). Adding Kafka now would be
adopting a second event-transport technology with no requirement pulling it in — exactly the "integrate a
product just to pad a sponsor list" anti-pattern this research is supposed to catch.

```
WHY IT EXISTS
Vultr's managed distributed-log/event-streaming product for high-throughput pipelines needing partitioned
replay, multiple consumer groups, and long retention — a different problem shape than pub/sub fan-out.

WHAT PRODUCT REQUIREMENT IT SATISFIES
None currently locked for GhostRange. Decisions.md #4 explicitly defers Kafka "until multi-worker fan-out
actually needs replay/partitioning" and documents the reasoning in ADR-003.

WHAT WOULD BREAK/CHANGE WITHOUT IT
Nothing breaks by not adopting it now. If M1's event volume/fan-out assumptions turn out wrong (e.g. many
workers need independent replay of the same event stream, or event retention/audit becomes a hard
requirement beyond what Postgres-backed evidence already gives), Kafka becomes the correct escalation —
but that is a future ADR addendum, not a current integration.

HOW IT APPEARS IN THE ARCHITECTURE
It doesn't, in M1.

HOW IT WILL BE TESTED
N/A — not adopted.
```

**Verdict: REJECT for M1** (confirms, does not override, Decisions.md #4/ADR-003). Revisit only if a
concrete replay/partitioning requirement emerges.

---

## 11. Vultr API — auth model, rate limits, lifecycle operations

**FACT — auth:** Vultr API v2 uses bearer-token auth: `Authorization: Bearer ${VULTR_API_KEY}`, a
personal access token generated in account settings (API access must be explicitly enabled per account/
sub-account). [Enable API access](https://docs.vultr.com/platform/other/api/enable-user-api-access)

**FACT — rate limits:** Vultr enforces request-volume limits per originating IP; exceeding roughly 30
requests/second returns HTTP 429. Vultr's own guidance: minimize unnecessary calls, use exponential
backoff/retry on 429, spread traffic to avoid bursts.
[Rate limits doc](https://docs.vultr.com/support/platform/api/what-rate-limits-apply-to-the-vultr-api)

**FACT — core lifecycle endpoints relevant to programmatic range control:**
- List instances: `GET /v2/instances`
- Create instance: `POST /v2/instances` (fields per §4 above)
- Terminate instance: `DELETE /v2/instances/{instance-id}`
- Create VPC 2.0 network: `POST /v2/vpcs` (`region`, `description`, `v4_subnet`, `v4_subnet_mask`) —
  **correction 2026-09-26 (Agent 02/vultr-control, verified live against govultr v3 SDK source)**: the
  endpoint is `/v2/vpcs`, not `/v2/vpc2` as earlier drafted; `/v2/vpc2` doesn't exist on the current API.
  Also: the raw instance-create field to attach a VPC is `attach_vpc` (a list), NOT `vpc_ids` — `vpc_ids`
  is the Terraform resource attribute name (Terraform translates it to `attach_vpc` before calling the
  API). `packages/range-iac` is OpenTofu-based so `vpc_ids` remains correct there; `packages/vultr-control`
  speaks the raw REST API directly and correctly uses `attach_vpc`. Also confirmed live: instance `tags`
  is a flat list of opaque strings (no key/value structure), and VPCs/Firewall Groups have no `tags` field
  at all, only `description` — GhostRange ownership metadata is encoded as `ghostrange:key:value` strings
  in instance tags and `ghostrange;key=value;...` in VPC/Firewall Group `description` (see
  `packages/vultr-control/README.md`).
- Create snapshot: `POST /v2/snapshots` (`instance_id`, `description`) — Vultr's own docs note this can
  take 20–30 minutes depending on instance size, i.e. **not instantaneous**, which matters for any
  "fork now" latency budget GhostScheduler assumes.
- Bandwidth/usage: `POST`-style query to `/v2/instances/{instance-id}/bandwidth` — Vultr explicitly warns
  this data is periodically refreshed and **not suitable for real-time metrics**.
[Vultr API reference](https://www.vultr.com/api/)

**OUR INTERPRETATION:** The auth model (simple bearer token) is easy to wrap in `packages/vultr-control`
with no OAuth complexity. The rate limit (~30 req/s per IP) is a real constraint GhostScheduler must
respect if many parallel forks each trigger instance-create calls near-simultaneously — `vultr-control`
should centralize all Vultr API calls behind a client that implements backoff/retry and, ideally, request
queuing/batching, rather than letting every worker hit the API independently. The snapshot-latency figure
(20–30 min) is an important correction to any assumption that "forking a world" via snapshot-restore is
instant — it is fast *relative to full re-provisioning*, but the *first* snapshot of a base image still
takes real wall-clock time, so GhostScheduler's fork strategy should snapshot base images ahead of need
(pre-warmed golden snapshots) rather than snapshotting on the critical path of a fork request.

```
WHY IT EXISTS
A conventional REST API with token auth and per-IP rate limiting — standard practice for a multi-tenant
cloud control plane to prevent abuse and ensure fair usage.

WHAT PRODUCT REQUIREMENT IT SATISFIES
"Programmatic instance lifecycle" is the literal mechanism by which GhostRange creates/destroys worlds.
The rate limit and snapshot-latency facts directly inform GhostScheduler's design constraints (must not
assume unlimited concurrent API calls or instant snapshot forking).

WHAT WOULD BREAK/CHANGE WITHOUT IT
This is the substrate everything else depends on — without an API, there's no automation, period. The
specific numbers (30 req/s, 20-30 min snapshot) matter because designing GhostScheduler against wrong
assumptions (e.g. assuming instant forking) would produce a scheduler that stalls or fails silently
against real Vultr behavior.

HOW IT APPEARS IN THE ARCHITECTURE
`packages/vultr-control` is the single choke point for all Vultr API calls: wraps auth, implements
backoff/retry on 429, and exposes an interface (create/list/terminate instance, create VPC, create
snapshot) that `range-iac`/`range-runtime` consume — no other package talks to Vultr directly. This
centralization is also a safety-boundary point: per Decisions.md #9, if API-call authority needs to be
gated by a range-ownership token/allowlist, this is the one place that check lives.

HOW IT WILL BE TESTED
`packages/vultr-control` ships a mock/fake client implementing the same interface for all unit/integration
tests (no live credentials in CI). A contract test asserts the mock and the real client expose identical
method signatures. Rate-limit/backoff logic is tested by injecting synthetic 429 responses into the mock
and asserting retry-with-backoff behavior, not by hitting the real API repeatedly.
```

**Verdict: ADOPT — this is the actual foundation**, not a nice-to-have; everything else in this document
is a statement about what that API surface can express.

---

## 12. Monitoring / telemetry APIs

**FACT:** Vultr exposes per-instance monitoring in the console (vCPU, disk ops, network bytes) and an API
bandwidth endpoint (`/v2/instances/{id}/bandwidth`) explicitly documented as periodically-refreshed, not
real-time. VKE has documented compatibility with external observability tooling (**NEEDS
VERIFICATION** — I could not confirm the exact list of "compatible observability tools" beyond the doc's
existence; likely standard Prometheus/Kubernetes-metrics-server style integration, but I did not verify
specifics). I found no evidence of a push-based or streaming telemetry API (e.g. no equivalent of a
metrics-streaming webhook) beyond the metadata service (self-query only, not external monitoring) and the
bandwidth polling endpoint.

**OUR INTERPRETATION:** Vultr's own telemetry is coarse and pull-based, explicitly not real-time. For
GhostRange, this means: **do not build GhostScheduler's compute-allocation decisions on Vultr's own
bandwidth/usage API as a live signal** — it's the wrong tool (Vultr says so directly). Real-time
observability inside a cyber-world (what an investigating agent needs to see, e.g. process activity,
auth logs, network flows for detection) has to come from agents/collectors running *inside* the range
assets themselves (via cloud-init-installed collectors, or CALDERA's own telemetry) and reported through
GhostRange's own event system (`packages/events`, Valkey pub/sub), not from the Vultr control-plane API.
Vultr's bandwidth endpoint may still be useful for coarse cost/usage accounting, just not for anything
latency-sensitive.

```
WHY IT EXISTS
Vultr's monitoring surface answers "how is my infrastructure billing/behaving at a coarse level," aimed
at account-level cost/capacity visibility, not application-level real-time observability.

WHAT PRODUCT REQUIREMENT IT SATISFIES
Coarse resource/cost accounting for the compute layer only (e.g. "how much bandwidth did world X's assets
use this month" for cost attribution). It does not and cannot satisfy the investigation-telemetry
requirement (an agent watching an incident unfold inside a world in near-real-time).

WHAT WOULD BREAK/CHANGE WITHOUT IT
Nothing core breaks — GhostRange's actual telemetry path was never going to be this API. Its absence as
a real-time signal is a documented Vultr limitation we must design around, not a gap we introduced.

HOW IT APPEARS IN THE ARCHITECTURE
At most, an optional coarse cost-tracking job in `packages/vultr-control` that periodically polls
bandwidth for accounting dashboards — explicitly not on any decision-making critical path. In-range
telemetry is entirely the domain of `packages/events` + evidence collectors, unrelated to this API.

HOW IT WILL BE TESTED
If the coarse cost-polling job is built, it's tested like any other `vultr-control` API call (mocked
client, no live credentials). No test asserts real-time behavior from this endpoint, matching Vultr's own
documented caveat.
```

**Verdict: ADOPT narrowly (coarse cost accounting only), REJECT as a real-time signal source** — and
flag this explicitly so no future agent designs GhostScheduler around a telemetry API that Vultr's own
docs say isn't real-time.

---

## Summary table

| Capability | Verdict | Where it lands |
|---|---|---|
| Cloud Compute (CPU instances) | **ADOPT** | Range assets + (later) orchestration fleet |
| Cloud GPU | DEFER | Optional future local-inference path only |
| Serverless Inference | DEFER | Optional alternative to self-hosted GPU inference |
| Instance templates/snapshots/cloud-init/startup scripts | **ADOPT** | Core RangeSpec compilation target (ADR-006) |
| VPC 2.0 + Firewall Groups | **ADOPT** | Per-world network isolation, safety boundary at network layer |
| VKE | ADOPT (design, 2026-09-27) for control-plane manifests; real cluster NOT_RUN pending approval / REJECT (range assets, unchanged) | `deploy/k8s/` (Kustomize base+overlays), `docs/deployment/VKE_DEPLOY.md` |
| Object Storage | **ADOPT** | Evidence/artifact persistence beyond world lifetime |
| Managed Postgres (+ pgvector) | **ADOPT** (pgvector: DEFER) | Contracts/schema store; pgvector optional for future retrieval |
| Managed Valkey | **ADOPT** (already locked, now confirmed) | Event transport (Decisions.md #4) |
| Managed Kafka | **REJECT** for M1 | Confirms Decisions.md #4 / ADR-003, revisit only if replay/partitioning need emerges |
| API (auth/rate limits/lifecycle) | **ADOPT** | Foundation of `packages/vultr-control`; scheduler must respect 30 req/s + snapshot latency |
| Monitoring/telemetry API | ADOPT narrowly (cost only) / REJECT as real-time signal | Not on any decision-making path; in-range telemetry comes from our own events system |

Items marked NEEDS VERIFICATION throughout this document (VPC gen-1 legacy status, exact Dec-2025 AMD GPU
preemptible plan announcement, exact VKE-compatible observability tool list) should be re-checked against
`docs.vultr.com` before any demo-day claim is made about them specifically — none of them affect the
ADOPT/REJECT verdicts above, which rest on the more firmly documented facts.
