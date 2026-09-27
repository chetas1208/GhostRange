# Evidence & Provenance Chain

- **Status:** Accepted (M1 baseline)
- **Owner:** Agent 14/15 (Backend Architect + Event-System Engineer)
- **Backs:** `packages/contracts/ghostrange_contracts/{evidence,verification,execution_graph,hypothesis}.py`

## Why this exists

GhostRange's entire value proposition is that a conclusion ("this
remediation closes the vulnerability") is not just asserted by an agent —
it is *traceable* back to the concrete bytes that justify it. Every
conclusion an agent, the scheduler, or a human relies on must resolve to a
chain of real objects, not a free-floating claim. This document describes
that chain concretely, in terms of the actual Pydantic models that
implement it in `packages/contracts`.

## The chain

```
CLAIM -> VERIFICATION -> OBSERVATION -> EXECUTION -> WORLD -> ARTIFACT
```

Read left to right as "what backs what":

- A **Claim** is backed by one or more **Verifications**.
- A **Verification** is backed by one or more **Observations**.
- An **Observation** was noticed during an **Execution** (an
  `ExecutionRecord`).
- An **Execution** happened inside a **World**.
- Both **Observations** and **Executions** may point at concrete
  **Artifacts** — the content-addressed bytes (logs, pcaps, screenshots)
  that are the actual physical evidence.

### 1. Claim (`ghostrange_contracts.evidence.ClaimV1`)

An assertion an agent puts forward, e.g. *"Remediation R closes the
exposed RDP port on dc01"*.

Fields: `id`, `world_id`, `statement`, `made_by_agent_id`, `confidence`
(0–1), `verification_ids: list[Id]`, `created_at`.

A Claim starts with zero `verification_ids` and accumulates them as
Verifications complete. A Claim's `confidence` is the *claimant's* stated
confidence, not the verified truth value — that distinction is exactly why
Verification exists as a separate step instead of trusting the claimant.

### 2. Verification (`ghostrange_contracts.verification.VerificationV1`)

An attempt to check whether a specific Claim holds, run by one of four
methods (`VerificationMethod`): `ADVERSARIAL_ATTACK` (an adversary agent
tries to break the claimed remediation), `STATIC_ANALYSIS`,
`RE_EXECUTION` (re-run the original scenario and check the outcome
differs), or `PEER_REVIEW` (another agent/human reviews the reasoning).

Fields: `id`, `claim_id`, `world_id`, `method`, `verifier_agent_id`,
`observation_ids: list[Id]`, `result` (`PENDING | PASSED | FAILED |
INCONCLUSIVE`), `reason`, `started_at`, `completed_at`.

A Verification's `result` is what actually updates a Claim's real-world
truth status (surfaced via `verification.passed` / `verification.failed`
events, see `packages/events`); a Verification is only as good as the
Observations it cites, which is why `observation_ids` is required to point
at real Observation records rather than being a free-text conclusion.

### 3. Observation (`ghostrange_contracts.verification.ObservationV1`)

A single discrete, timestamped fact noticed while an ExecutionRecord ran —
the smallest unit of evidence. `ObservationType` enumerates the kinds:
`FILE_STATE`, `PROCESS_STATE`, `NETWORK_TRAFFIC`, `LOG_LINE`,
`COMMAND_RESULT`, `AGENT_ASSERTION`.

Fields: `id`, `execution_id` (the `ExecutionRecordV1.id` it came from),
`world_id`, `agent_id`, `observation_type`, `summary`,
`raw_artifact_id: Optional[Id]`, `observed_at`.

`raw_artifact_id` is optional on purpose: an `AGENT_ASSERTION` observation
("I confirmed port 3389 is closed") may have no backing file at all, in
which case its evidentiary weight is lower than a `LOG_LINE` observation
that does point at a real Artifact — that asymmetry is visible in the data
model, not hidden in application logic.

### 4. Execution (`ghostrange_contracts.execution_graph.ExecutionRecordV1`)

The provenance record of one concrete run of a Task: this is where "who
ran what, on what compute, with what result" lives.

Fields: `id`, `task_id`, `world_id`, `agent_id`, `compute_worker_id`,
`command`, `status` (`RUNNING | SUCCEEDED | FAILED | TIMED_OUT`),
`exit_code`, `artifact_ids: list[Id]`, `started_at`, `completed_at`.

Every Observation traces back to exactly one ExecutionRecord via
`execution_id`; every ExecutionRecord traces back to exactly one Task
(`TaskV1`) and one World (`world_id`) and, when applicable, one
ComputeWorker (`compute_worker_id`) — so "what hardware/provider actually
produced this evidence" is always answerable, which matters both for
adversarial verification (was this run on an isolated GhostRange-owned
worker, per the safety boundary) and for cost accounting.

### 5. World (`ghostrange_contracts.world.WorldV1`)

The branch (forked or root) the Execution ran inside. `world_id` appears
directly on Claim, Verification, Observation, and ExecutionRecord — not
just transitively through Execution — so any evidence object can be
filtered/scoped to a World without walking the whole chain. This
deliberate denormalization is why the frontend's per-World evidence panel
doesn't need to join through Execution to know which World an Observation
belongs to.

### 6. Artifact (`ghostrange_contracts.evidence.ArtifactV1`)

The leaf: concrete, content-addressed bytes.

Fields: `id`, `world_id`, `produced_by_execution_id`, `artifact_type`
(`LOG | PCAP | SCREENSHOT | MEMORY_DUMP | FILE | COMMAND_OUTPUT | REPORT`),
`storage_uri`, `hash_algorithm` (`SHA256`), `content_hash` (validated as a
64-char lowercase hex digest — malformed hashes are rejected at
construction, not merely at "someone eventually checks"), `size_bytes`,
`created_at`.

Two Artifacts with the same `content_hash` are the same bytes, full stop,
regardless of which World or ExecutionRecord produced them — this is what
makes the chain *tamper-evident*: if an Artifact referenced by an
Observation is later re-fetched from `storage_uri` and its hash no longer
matches `content_hash`, the evidence is provably invalid, independent of
any application-level access control.

## The bundling object: Evidence (`ghostrange_contracts.evidence.EvidenceV1`)

`EvidenceV1` is not a seventh link in the chain — it is the object that
*ties the chain together* for presentation and for the `evidence.created`
event: it references exactly one `claim_id` and one `verification_id`,
requires at least one `observation_ids` entry (`min_length=1` — evidence
with zero observations is rejected at construction, not a valid "empty"
state), and carries `artifact_ids` plus its own `content_hash` (a digest
over the bundle, for provenance chaining at the bundle level in addition
to per-Artifact hashes).

Fields: `id`, `world_id`, `claim_id`, `verification_id`,
`observation_ids: list[Id]` (≥1), `artifact_ids: list[Id]`, `summary`,
`content_hash`, `created_at`.

This is the object a human or downstream agent is actually shown as "why
we believe this": *"Claim X was verified by Verification Y, based on
Observations [...], backed by Artifacts [...]."*

## Worked example

1. An investigator agent proposes `HypothesisV1("RDP is exposed on
   dc01")`.
2. A remediator agent applies `RemediationV1` (closes port 3389) inside a
   forked `WorldV1`.
3. That agent asserts `ClaimV1("Remediation closes the exposed RDP
   port")`, `confidence=0.75`.
4. An adversary agent runs an `AttackAttemptV1` (`technique_id="T1021.001"`,
   RDP) against the remediated World, producing an `ExecutionRecordV1`
   with `status=SUCCEEDED` and one `artifact_ids` entry (a pcap of the
   connection attempt).
5. From that ExecutionRecord, an `ObservationV1`
   (`observation_type=NETWORK_TRAFFIC`, `summary="connection attempt to
   3389 refused"`, `raw_artifact_id=<the pcap Artifact>`) is recorded.
6. A verifier agent runs a `VerificationV1`
   (`method=ADVERSARIAL_ATTACK`, `observation_ids=[<step 5 id>]`,
   `result=PASSED`).
7. An `EvidenceV1` bundle is created referencing that Claim, that
   Verification, that Observation, and the pcap Artifact — and
   `evidence.created` is published (`packages/events`) carrying
   `evidence_id`, `world_id`, `claim_id`, `verification_id`,
   `artifact_ids`, `content_hash`, so the frontend can render the bundle
   without a follow-up query.

If instead the attack had succeeded (RDP still reachable), step 6's
`VerificationV1.result` would be `FAILED`, `verification.failed` would
fire instead of `verification.passed`, and the Claim's confidence must be
treated by downstream consumers as refuted, not merely "unconfirmed" —
the model does not auto-update `ClaimV1.confidence` on verification
result; that reconciliation is intentionally left to
`packages/evidence` (Agent 12's ownership) rather than baked into the
contract layer, since *how* a failed verification should move a claim's
stated confidence is a policy decision, not a schema one.

## Open questions (owned by Agent 12, `packages/evidence`)

- Whether Artifact storage is content-addressed end-to-end (dedup by hash
  across Worlds) or an append-only hash-chained log per World — flagged
  as undecided in `Decisions.md`. `ArtifactV1.content_hash` supports
  either; the storage/dedup strategy is an implementation detail of
  `packages/evidence`, not a contract-level decision.
- Whether `EvidenceV1.content_hash` should itself be a Merkle root over
  its `observation_ids`/`artifact_ids` (so the bundle hash changes iff its
  members change) — not yet enforced by validation; currently the caller
  computes and supplies it.
