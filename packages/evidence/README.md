# ghostrange-evidence

Artifact storage, deterministic scenario verification, and provenance-
chain queries backing GhostRange's evidence chain:

```
CLAIM -> VERIFICATION -> OBSERVATION -> EXECUTION -> WORLD -> ARTIFACT
```

See `docs/architecture/EVIDENCE.md` for the full narrative and the actual
Pydantic field names this package builds on
(`packages/contracts/ghostrange_contracts/{evidence,verification,execution_graph,world}.py`).
This package is the *implementation* behind those contracts: where
artifact bytes actually live, how a claim's full evidence chain is
actually queried, and how M2's controlled scenario decides its verdict.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e packages/contracts
pip install -e packages/evidence
# with test deps:
pip install -e "packages/contracts[dev]" -e "packages/evidence[dev]"
# only if you need VultrObjectStorageStore against a real bucket:
pip install -e "packages/evidence[vultr]"
```

## Design decision: content-addressed storage, not a hash-chained log

`docs/architecture/EVIDENCE.md` and `Decisions.md` both flag this as the
open question owned by this package. **Resolved: content-addressed,
keyed directly by the SHA-256 `content_hash` `ArtifactV1` already
validates at construction.** Full reasoning lives in the module docstring
of `ghostrange_evidence/object_store.py`; in short:

1. `ArtifactV1.content_hash` already exists and is already what every
   other consumer (events, provenance queries, the Evidence 3D view) keys
   off of — a hash chain would need a second, parallel identifier nothing
   else expects.
2. Tamper-evidence is already inherent to content-addressing (bytes that
   don't hash to their claimed digest are provably invalid on read); a
   hash chain's extra guarantee (no entry was ever deleted from the
   sequence) answers a question nothing in this product asks — every real
   consumer asks "is *this* Artifact still what it claims to be," a
   per-object question.
3. Dedup is free and actually matters for a scenario that forks Worlds to
   compare remediations side by side (`ghostrange-auth-lab-v1` and
   friends): the same boilerplate log preamble/response body recurs across
   many Worlds/Executions, and content addressing stores it once, globally.
4. It maps directly onto Vultr Object Storage's S3-compatible API
   (`docs/research/VULTR.md` §7, ADOPTed there for this exact purpose):
   the content hash *is* the object key, no separate chain-position index
   to keep consistent.

Accepted trade-off: this alone doesn't prove *when* something was first
written or that nothing was ever deleted from a World's evidence set. If
that stronger guarantee is ever needed (e.g. a compliance audit trail),
the fix is an additive append-only *index* on top of this store — which is
exactly what `ProvenanceStore` already is (an ordered record of what was
registered), not a replacement of the content-addressed blob layer.

## Artifact storage

```python
from ghostrange_contracts.enums import ArtifactType
from ghostrange_evidence import ArtifactStore, LocalFilesystemObjectStore

store = ArtifactStore(LocalFilesystemObjectStore("/var/ghostrange/evidence"))

artifact = store.put_bytes(
    raw_response_bytes,
    world_id=world.id,
    artifact_type=ArtifactType.COMMAND_OUTPUT,
    produced_by_execution_id=execution.id,
)  # -> real ArtifactV1, hash computed here, bytes stored immutably

raw = store.get_bytes(artifact)  # re-verifies hash on every read
```

- Storing the same bytes twice (even from different Worlds/Executions)
  dedups at the object-storage layer but still yields two distinct
  `ArtifactV1` records — the bytes are deduplicated, the *evidence record
  of who produced/referenced them* is not.
- Storing *different* bytes under a key that already holds content raises
  `ObjectIntegrityError` — overwriting existing content at a given hash is
  structurally impossible through this API.
- Reading back an artifact whose stored bytes no longer hash to
  `content_hash` raises `ArtifactTamperedError` rather than silently
  returning the wrong bytes.

For Vultr Object Storage (S3-compatible, `docs/research/VULTR.md` §7):

```python
from ghostrange_evidence import ArtifactStore, VultrObjectStorageStore

store = ArtifactStore(VultrObjectStorageStore(
    bucket="ghostrange-evidence",
    endpoint_url="https://ewr1.vultrobjects.com",
    access_key=...,
    secret_key=...,
))
```

No live Vultr credentials are available in this environment, so this
backend is exercised in `tests/test_object_store.py` against a
hand-written fake S3 client implementing the exact subset of the boto3
surface this class calls (`head_object`/`get_object`/`put_object`) — the
overwrite-refusal and dedup logic being tested is backend-agnostic Python,
not boto3 internals, so this is a real test of the actual logic, not a
mock that asserts nothing. A **gated manual test** (round-trip a real
upload/download against a real bucket) is the intended live-credential
check, mirroring the testing plan `docs/research/VULTR.md` §7 already
lays out for this integration, and matching how Agent 02
(`packages/vultr-control`) is expected to handle the absence of live
credentials in this environment.

## Deterministic scenario verification (`ghostrange-auth-lab-v1`)

```python
from ghostrange_evidence import evaluate_auth_lab_v1, verdict_to_verification_result

result = evaluate_auth_lab_v1(observations)  # list[ObservationV1]
result.verdict       # AuthLabVerdict.EXPECTED_CONDITION_OBSERVED | _NOT_OBSERVED | INCONCLUSIVE
result.rationale      # human-readable, built from the matched rule, not a model
verdict_to_verification_result(result.verdict)  # -> VerificationResult for VerificationV1.result
```

**Explicitly not an LLM judgment call.** The verdict is pure rule
evaluation over `ObservationV1.summary` text (case-insensitive literal
keyword matching, no fuzzy matching, no model call) — see
`ghostrange_evidence/scenario_verification.py` for the exact marker lists
and the single-counterexample-wins priority rule (one unexpectedly
permissive response outweighs any number of correct-rejection
observations, mirroring `EVIDENCE.md`'s own worked example).

**ASSUMPTION — flagged for confirmation with Agent 06** (controlled
scenario engineer; `ranges/ghostrange-auth-lab-v1/` was empty when this
was written, so Agent 06 had not yet defined the real harness output
shape): the scenario provisions an auth service, and the expected
(secure/remediated) condition is that a request using a known-bad/invalid
credential is rejected — no session or success response issued. The
scenario specifically watches for regressions where the service is
*unexpectedly permissive*. If Agent 06's real harness tags observations
differently, only the marker-matching in `scenario_verification.py`
should need to change — the function signature
(`list[ObservationV1] -> AuthLabVerdictResult`) and the
single-counterexample-wins verdict logic should not.

## Provenance queries

`ProvenanceStore` is the query engine the Evidence 3D view (a separate
frontend session, consuming this indirectly via whatever API layer
apps/api exposes) is expected to eventually query against. Shape:

```python
from ghostrange_evidence import ProvenanceStore

store = ProvenanceStore()
store.register_world(world)
store.register_execution_record(execution)
store.register_artifact(artifact)
store.register_observation(observation)
store.register_verification(verification)
store.register_claim(claim)
store.register_evidence(evidence)

chain = store.get_provenance_chain(claim.id)
chain.claim                          # ClaimV1
chain.verification_status            # "UNVERIFIED" | "VERIFIED" | "REFUTED"
chain.evidence                       # tuple[EvidenceChainLink, ...]
chain.evidence[0].evidence           # EvidenceV1
chain.evidence[0].verification       # VerificationV1
chain.evidence[0].bundle_artifacts   # tuple[ArtifactV1, ...] (EvidenceV1.artifact_ids)
chain.evidence[0].observations       # tuple[ObservationChainLink, ...]
chain.evidence[0].observations[0].observation        # ObservationV1
chain.evidence[0].observations[0].execution_record   # ExecutionRecordV1
chain.evidence[0].observations[0].world              # WorldV1
chain.evidence[0].observations[0].artifacts          # tuple[ArtifactV1, ...]
```

A Claim with no Evidence registered yet returns `chain.evidence == ()` —
this is a normal, non-error state ("nothing verified this yet"). A
reference that *is* present but doesn't resolve (e.g. an `EvidenceV1`
pointing at a `verification_id` nobody registered) raises
`UnknownReferenceError` distinctly, because that's a data-integrity bug,
not an absence-of-evidence state.

This is an in-memory reference implementation (dicts + reverse indices)
appropriate for M2's single-process scope. Per `docs/research/VULTR.md`'s
own plan ("Postgres holds metadata/pointers, not the blobs themselves"),
swapping the backing store for real Postgres later should only require
re-implementing `ProvenanceStore`'s public methods against SQL — no
caller-visible shape change, since none of the query methods leak the
fact that they're currently dict lookups.

## A claim with zero evidence cannot be marked verified

`ClaimV1` (contracts) deliberately has no `verified`/`status` field of its
own — `EVIDENCE.md` flags "how a failed verification should move a
claim's stated confidence" as "a policy decision, not a schema one," left
to this package. `ProvenanceStore.mark_claim_verified(claim_id)` is that
policy:

- Raises `NoEvidenceError` if the claim has zero registered `EvidenceV1`
  bundles — the structural gate this milestone requires. There is no code
  path in this package that reaches `VERIFIED` without a real Evidence
  bundle backing it.
- Additionally re-checks that every registered `EvidenceV1` has at least
  one `observation_ids` entry (defense-in-depth alongside — not a
  replacement for — the `min_length=1` constraint `packages/contracts`
  already enforces at construction time), since this store's
  registration API accepts already-built model instances and cannot
  assume every caller went through real Pydantic validation.
- Otherwise derives `VERIFIED` (any linked `VerificationV1.result ==
  PASSED`), `REFUTED` (none passed but at least one `FAILED`), or leaves
  `UNVERIFIED` (e.g. all `PENDING`/`INCONCLUSIVE`).

## Tests

```bash
pip install -e "packages/contracts[dev]" -e "packages/evidence[dev]"
python3 -m pytest packages/evidence/tests -v
```

Covers: hash immutability (overwrite attempts raise, at both the raw
`ObjectStore` layer and end-to-end through `ArtifactStore`), read-time
tamper detection, verification determinism (same observations always
produce the same verdict, input never mutated), full provenance chain
traversal correctness (reconstructing `EVIDENCE.md`'s own 7-step worked
example and asserting every level resolves correctly, including dedup of
an artifact reachable via two different paths), dangling-reference
detection, and the zero-evidence-cannot-verify guarantee.
