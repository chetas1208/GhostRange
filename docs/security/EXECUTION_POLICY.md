# GhostRange Execution Policy

Owner: Agent 13 (Security Boundary Engineer). Status: v1, locked context per
`Decisions.md` item 9 ("safety boundary enforced in `packages/execution-graph`
+ a policy-check service, not in prompts"). Companion documents:
`docs/security/THREAT_MODEL.md` (threat IDs T1-T17 referenced below) and,
new in M2, `docs/security/RANGE_NETWORK_BOUNDARY.md` (the concrete network
boundary for the first real range, `ghostrange-auth-lab-v1`, including a
correction to this document's §5 egress framing — read that document's §3
before treating §5 below as literally accurate for a live Vultr account).

This document specifies **the concrete enforcement mechanism**. Every clause
answers "what code, running where, checks what, and does what on failure" —
not "the agent should."

**M2 implementation status (Agent 05):** the data shapes this document
names as "conceptually, final shape lives in packages/contracts" (§2, §3.1,
§8) are now real: `RangeOwnershipTokenV1`, `ExecutionRequestV1`,
`ExecutionTicketV1`, `PolicyDecisionV1`, `ActorRef`, `ProvenanceRef`,
`AuditRecordV1` all exist in `packages/contracts/ghostrange_contracts/
policy.py`. The `authorize()` function specified in §3.2 is implemented,
with the exact same seven checks and hard-fail-via-exception semantics, in
the new `packages/policy-check` package (`PolicyCheckService.authorize()`),
including token/ticket signing (`TokenSigner`), the registry re-derivation
source of truth (`PolicyRegistry`), the hash-chained audit log
(`AuditLog`), the SSRF backstop named in §6/T6 (`ssrf_guard`), the
model-output→target resolution path named in §3.1 (`model_output_guard.
resolve_target`), and the logging-redaction backstop named in §6
(`secrets.redact_secrets`). See `packages/policy-check/README.md` for the
calling interface Agent 07 (execution harness) and Agent 04 (range
runtime) should build against, and that package's `tests/` for the
required negative-path proof (off-range target, expired token, disallowed
action category, token spoofing, unreviewed ability, quota exceeded,
missing approval — each asserted to actually deny, not merely documented
as denied). The registry/audit-log storage in this M2 pass is in-memory
and process-local, not yet the Postgres-backed, append-only-granted
deployment this document's §4/§8 describe — treat it as a correctness-
proven stub, not a production deployment, until that storage layer lands.

## 1. Where this lives, architecturally

**The policy-check service is a separate deployable component from
`packages/execution-graph`.** This separation is the whole point: if it were
just a function inside execution-graph's own process, a sufficiently
successful prompt injection that achieves code-execution-equivalent influence
over the orchestrator process (e.g. by getting the agent to call a
"run arbitrary Python" debug tool some future dev leaves in) could in
principle patch it out. As a standalone service it can only be influenced
through its network API, using a request schema the agent cannot redefine.

```
packages/execution-graph          services/policy-check           packages/{adversary-adapter,
(task scheduling, DAG,                  (this doc)                 range-runtime, vultr-control}
declares WHAT a task wants                                          (this doc's downstream executors)
to target — never decides
whether it's allowed)

   TaskV1 { task_id, world_id,
     range_id, target_refs,
     action_category, params }
              │
              │ 1. authorize(request, token)          [synchronous, blocking, fail-closed]
              ▼
     ┌──────────────────────┐
     │   POLICY-CHECK        │── registry DB (range-ownership tokens, canonical target sets,
     │   SERVICE              │   quota counters, approvals) — SOURCE OF TRUTH, never trusts
     │                         │   anything the caller claims about its own authorization
     │  - verify token sig    │
     │  - re-derive canonical │── audit log (append-only, hash-chained) — every call, allow or deny
     │    target set (DB)     │
     │  - check subset        │
     │  - check capability    │
     │  - check quota         │
     │  - check approval      │
     │    (if required cat.)  │
     └───────────┬────────────┘
                 │ 2. on ALLOW: issue single-use, request-hash-bound
                 │    execution-authorization ticket (short TTL, signed)
                 │    on DENY: hard fail, structured reason, audit record
                 ▼
     adversary-adapter / range-runtime / vultr-control
     re-validate ticket signature + hash BEFORE performing the
     side-effecting call (defense in depth — see §3.4)
```

`packages/execution-graph` is a client of policy-check, exactly like every
other execution-issuing package. It has no special bypass, and no package in
this system is permitted to call CALDERA, the Vultr API, or range-runtime's
provisioning/teardown APIs without first holding a valid authorization ticket
for that exact request. This is enforced by code review convention **and**
by the executors' own re-check (§3.4), not by trust in call sites.

## 2. Range-ownership token — data structure and semantics

Conceptually (final shape lives in `packages/contracts` following the
project's `VersionedModel` convention — `RangeOwnershipTokenV1`):

```python
class RangeOwnershipTokenV1(VersionedModel):
    token_id: Id                       # uuid4, unique per issuance
    world_id: Id                       # binds token to exactly one forked world
    range_id: Id                       # binds token to exactly one range within that world
    target_set: list[TargetRef]        # canonical member list — hosts/IPs/CIDRs that
                                        # ACTUALLY exist in this range, per IaC apply output
    capabilities: list[AbilityCategory]  # e.g. RECON, EXPLOIT, PERSISTENCE, EXFIL_SIM —
                                        # MITRE-tactic-shaped allowlist of what kinds of
                                        # abilities this token authorizes, independent of target
    issued_at: AwareDatetime
    expires_at: AwareDatetime          # short-lived; re-issued automatically by range-runtime
                                        # on renewal, never extended by any other caller
    issuer_signature: str              # HMAC/JWT signature; signing key held only by
                                        # range-runtime + policy-check, never by execution-graph
                                        # and never observable by the agent
```

**Minting**: tokens are minted **exclusively** by `packages/range-runtime`,
**exclusively** at the moment a range finishes provisioning — i.e. after
OpenTofu apply succeeds and the range's real member IPs are known. This
ordering matters: `target_set` is always ground truth (what actually got
provisioned), never aspirational (what a RangeSpec merely requested). There
is no API endpoint, anywhere in the system, that accepts "mint me a token"
as an agent-triggerable action. Token minting is a side effect of the
provisioning pipeline, gated upstream by an approved `RangeSpecV1` (itself
either template-driven or human-approved — never agent-authored free text
that becomes infra).

**Checking**: a token is never trusted at face value for its *contents* —
only its *signature* and *non-expiry* are checked cryptographically; the
actual `target_set` used for the authorization decision is **re-fetched from
policy-check's registry by `range_id`** on every call, not read out of the
token the caller presented. This means even a leaked-but-unexpired token
cannot be used to authorize a target added to the token after the fact by
tampering with a cached copy — the registry, not the bytes in flight, is
authoritative.

**Scope discipline**: `world_id`-bound, `range_id`-bound, time-bound,
capability-bound. A token for World A / Range 1 with `RECON` capability
cannot authorize an `EXPLOIT` action, cannot authorize any target outside
Range 1, and cannot authorize anything in World B, ever — regardless of what
text accompanies the request.

## 3. The authorization check

### 3.1 What a task declares (the input side)

`packages/contracts` defines (conceptually) a task's target declaration as
part of `TaskV1`:

```python
class TargetRef(GhostRangeModel):
    range_id: Id
    host_or_ip: str   # constrained: must match a member already enumerated
                       # in that range's IaC output at DAG-compile time —
                       # NOT free text the agent can invent

class TaskV1(VersionedModel):
    task_id: Id
    world_id: Id
    range_id: Id
    target_refs: list[TargetRef]      # fixed at DAG compile time
    action_category: AbilityCategory
    ability_ref: str                  # must resolve against the reviewed
                                       # CALDERA ability catalog (T11) — no
                                       # inline/novel ability bodies accepted
    params: dict                      # ability parameters only, never targets
```

`execution-graph` compiles the DAG — including every node's `target_refs` —
**before** the agent begins reasoning about that node's execution. The
agent's role is to select among already-compiled task nodes / parameterize
within their existing schema (e.g. choose *which* pre-declared target from
the node's own list, choose ability params within the catalog entry's
declared parameter schema) — it cannot widen `target_refs` after the fact.
Any attempt to construct a `TargetRef` outside the range's enumerated
members fails **Pydantic validation** (`extra="forbid"`, constrained pattern)
before the request is even well-formed enough to send to policy-check. This
is the first of two independent enforcement layers (schema, then service).

### 3.2 `authorize()` — the check, precisely

```python
def authorize(request: ExecutionRequestV1, token: RangeOwnershipTokenV1) -> PolicyDecisionV1:
    # 1. Token integrity — cryptographic, not textual
    if not verify_signature(token, policy_check_public_key):
        return deny("BAD_TOKEN_SIGNATURE")
    if token.expires_at < now():
        return deny("TOKEN_EXPIRED")
    if token.world_id != request.world_id or token.range_id != request.range_id:
        return deny("TOKEN_SCOPE_MISMATCH")

    # 2. Re-derive canonical truth — never trust the request's own claims
    canonical_targets = registry.get_target_set(request.range_id)   # DB read, source of truth
    if not set(request.target_refs) <= set(canonical_targets):
        return deny("TARGET_NOT_IN_RANGE")          # <-- T5, T10 primary backstop

    # 3. Capability check
    if request.action_category not in token.capabilities:
        return deny("CAPABILITY_NOT_GRANTED")

    # 4. Ability catalog check (T11)
    if not catalog.is_reviewed_ability(request.ability_ref):
        return deny("ABILITY_NOT_IN_CATALOG")

    # 5. Quota check (T13)
    if not quotas.admit(request.world_id, request.resource_cost):
        return deny("QUOTA_EXCEEDED")

    # 6. Human-approval-required categories (T15, §7)
    if request.action_category in HUMAN_APPROVAL_REQUIRED:
        approval = registry.get_approval(request_hash(request))
        if approval is None or approval.expired():
            return deny("HUMAN_APPROVAL_REQUIRED")

    # 7. Absolute deny list — not overridable by any approval (T5)
    if not set(request.target_refs) <= set(canonical_targets):
        # (redundant with #2 by construction — target ⊄ GhostRange-owned range
        #  is never reachable via an approval path; there is no ALLOW branch
        #  for "approve an off-range target," only deny)
        return deny("OFF_RANGE_TARGET_ABSOLUTE_DENY")

    ticket = issue_ticket(request_hash(request), ttl=SHORT_TTL, single_use=True)
    audit.append(ALLOW, request, token, ticket)
    return allow(ticket)
```

**On any deny**: this is a **hard fail**, not a warning. The structured
`PolicyDecisionV1{allowed: false, reason: ...}` is terminal for that task
node — `execution-graph` marks the node failed, does not retry with
different wording, does not fall back to a "degraded" execution path, and
does not let the agent's subsequent turn silently re-attempt the same
request under a different task_id without going through the same check
again (the check is per-request-hash, not per-task_id, so renaming doesn't
help). Every deny is written to the audit log with full request contents —
denials are signal, not noise, and are a primary detection surface for "the
agent is trying to escalate."

### 3.3 Fail-closed default

If policy-check is unreachable, slow, or returns anything other than a
well-formed `PolicyDecisionV1`, the default is **deny**. There is no
"assume allowed if the policy service is down" code path anywhere in
`adversary-adapter`, `range-runtime`, or `vultr-control`. Availability of the
safety boundary is a harder requirement than availability of execution.

### 3.4 Defense in depth: the ticket, re-checked by the executor

`authorize()`'s `ALLOW` response is not itself permission to act — it issues
a **short-lived, single-use execution-authorization ticket** cryptographically
bound to the exact hash of the authorized request. `adversary-adapter`,
`range-runtime`, and `vultr-control` each independently verify that ticket's
signature and hash-binding **immediately before** performing their
respective side-effecting call (submitting an ability to CALDERA, calling
the Vultr API, provisioning/tearing down infra). This means a compromise
that lets an attacker call the executor package directly (skipping
execution-graph and policy-check entirely) still cannot get a real
side-effecting call to happen without also forging a signature it has no
key for. Two independent checks (policy-check's decision, executor's ticket
re-validation), not one.

## 4. Policy-check service's own deployment posture

Named explicitly as a requirement, not assumed for free (see
THREAT_MODEL.md §5.5): policy-check is reachable only via authenticated
internal RPC (mTLS or signed service tokens) from other control-plane
services. It exposes no agent-reachable admin surface — there is no
"update the allowlist" HTTP route that the orchestrator's own API surface
proxies to; registry mutations (token issuance, approval records, quota
resets) happen only through range-runtime's provisioning pipeline and the
human-approval endpoint (§7), both of which are separately authenticated
and outside the agent's tool-call surface entirely.

## 5. Network egress control for range VMs

Enforced at the **cloud/VPC layer**, not inside the VM (the VM is assumed
hostile — see THREAT_MODEL.md T3):

- Each range/world is provisioned into its own Vultr VPC 2.0 network
  (`packages/range-iac`), with a security-group/firewall default of
  **deny-all egress**.
- Exactly one egress allow-rule is added per range: outbound from the
  range's CALDERA agent (Sandcat) to the CALDERA server's control-plane
  IP, on the CALDERA callback port only.
- A scoped internal-DNS allow-rule may be added if agent check-in needs
  name resolution — pointed at an internal resolver only, never at
  arbitrary public DNS, to avoid DNS-tunneling exfil paths.
- No rule permits range → control-plane API/DB/Redis, and no rule permits
  range → public Internet generally, and no rule permits range → another
  range's VPC (T9). These are separate, explicit non-rules (default-deny),
  not something that has to be remembered to add.
- Ingress into a range is limited to control-plane-initiated connections on
  the specific ports range-runtime's mediated evidence-collection proxy
  needs; ranges cannot initiate connections into the control plane at all
  (asymmetric by design).
- This is the second independent layer behind policy-check: even a
  hypothetical policy-check bypass cannot make a range VM reach a real
  target, because the network fabric itself has no route there.

## 6. Secrets isolation

- **What must never reach a range**: Vultr API key, CALDERA admin/operator
  API credential, Postgres credentials, Redis/Valkey credentials, the
  policy-check token-signing key.
- **How it's kept out**: `range-iac`'s cloud-init templates for range VMs
  contain no secret-typed fields at all — they are not parameterized with
  any of the above, so there is nothing to accidentally template in. The
  only credential material a range VM ever receives is a **CALDERA agent
  enrollment token**, fetched by range-runtime from the secrets manager on
  the range's behalf and injected at provisioning time, scoped narrowly to
  "enroll as an agent for range_id X, check in, post results" — a distinct,
  much lower-privilege credential from the CALDERA admin API key, enforced
  server-side by the CALDERA server's own auth model. This enrollment token
  is revoked at teardown (§9) and is never valid outside that range's
  lifetime.
- **Where real secrets live**: a secrets manager (Vault-compatible or
  Vultr-native equivalent) reachable only from the control-plane VPC.
  `range-runtime`, `vultr-control`, and `adversary-adapter` are the only
  readers, and each reads only the specific secret it needs at the moment
  it needs it (no long-lived in-memory secret caches passed between
  packages). No secret is ever logged, and the audit log (§8) is checked in
  code review to confirm request/response bodies it captures for
  provenance never include credential fields (structured logging with an
  explicit secret-redaction allowlist of field names, fail-closed: unknown
  fields are redacted by default, not passed through by default).
- **Why this holds even against a compromised range**: the range never had
  the secret, so there is nothing to steal locally, and the network
  boundary (§5) means it cannot reach the secrets manager's control-plane
  address to try. Two independent reasons, not one.

## 7. Human-approval-required boundary

Human approval is a **hard-coded property of an action category**, checked
inside `authorize()` (§3.2 step 6) exactly like any other precondition —
never a prompt instruction telling the agent to "ask before doing X." An
approval record is created only via a separate, human-authenticated
endpoint/UI action (not reachable from the agent's own tool surface), is
bound to the exact `request_hash` it approves (so it cannot be reused for a
different, even superficially similar, request), and expires.

**Categories requiring human approval before `authorize()` can return
ALLOW:**

| Category | Example | Why gated |
|---|---|---|
| Vultr spend beyond a world's pre-approved quota | Provisioning additional ranges beyond the day's planned budget | Cost control + prevents fork-explosion from silently escalating spend |
| Promoting a "verified" evidence record to an accepted finding | Marking a remediation as certified after re-verification | This is the evidence-acceptance gate (THREAT_MODEL.md T8) — a human checkpoint against poisoned-evidence chains even beyond the technical hash-chain check |
| Extending a range/world's TTL past its scheduled teardown | Requesting more time before automatic destruction | Prevents "just keep it alive a bit longer" from becoming indefinite residual attack surface |
| Adding a new CALDERA ability to the reviewed catalog | Onboarding a new Atomic Red Team technique | Prevents an unreviewed, potentially unbounded ability (e.g. one that shells out arbitrarily) from ever becoming callable |
| Any change to the policy-check registry's issuance rules, quota ceilings, or the token-signing key | Operational changes to the boundary itself | The boundary's own configuration is the highest-value target in the system; changing it must never be an agent-reachable action |

**Categories that are NOT on this list, deliberately, because they are not
approvable at all:**

- **Any target outside the requesting range's registered ownership token
  (i.e., "attack real, non-GhostRange-owned infrastructure").** This is not
  a human-approval-gated action — it is an **absolute deny with no override
  code path** (§3.2 step 7). Putting it on the approval list would imply a
  human *could* say yes; the architectural decision is that no one can,
  from inside this system. If GhostRange ever needs to touch something it
  doesn't own, that happens entirely outside this execution path (a
  separate, manually-operated process), never via an approval record that
  `authorize()` would accept.

This distinction — **absolute deny vs. approval-gated** — is itself
load-bearing: approval-gated actions are legitimate-but-sensitive things a
human can consciously authorize; the off-range case is excluded from that
mechanism entirely so that no compromised or socially-engineered approval
flow can ever be the path by which GhostRange attacks something it doesn't
own.

## 8. Immutable audit trail — concrete shape

Every `authorize()` call (allow or deny), every token issuance, every
approval decision, and every teardown event produces one record:

```python
class AuditRecordV1(VersionedModel):
    seq: int                    # monotonic, gapless within a shard
    prev_hash: str              # hash of the previous record — hash-chained ledger
    timestamp: AwareDatetime
    actor: ActorRef             # {kind: AGENT|SERVICE|HUMAN, id, task_id/tool_call_id if agent}
    request_hash: str
    decision: Literal["ALLOW", "DENY"]
    reason: str | None          # populated on DENY (§3.2 codes)
    world_id: Id
    range_id: Id | None
    target_refs: list[TargetRef]
    provenance: ProvenanceRef   # {package, version/commit_hash, dag_node_id}
    signature: str              # signed by the audit service's key at write time
```

Storage: append-only, in a datastore/table where the application's own DB
role has **no UPDATE/DELETE grant** (Postgres `GRANT INSERT, SELECT` only —
enforced at the database level, not just by application discipline), so an
application-layer compromise or SQL injection cannot rewrite history, only
be caught trying (a failed UPDATE attempt against an append-only-granted
role is itself an anomaly worth alerting on). This is distinct from and
sits alongside `packages/evidence`'s own hash-chained evidence log
(THREAT_MODEL.md T8) — the audit trail records *authorization decisions*,
evidence records the *verification results themselves*; both are
append-only and signed, for the same reason.

**Command/tool provenance** on every record: which package + version/commit
issued the request, which DAG task node, which agent tool-call id, which
world/range, and (for approval-gated actions) which human approved it. This
lets a poisoned-evidence investigation cross-reference "what evidence
claims happened" against "what the audit trail says was actually
authorized and by what code," independently of anything the range itself
reported.

## 9. Resource quotas and teardown guarantees

- **Quotas** (checked in `authorize()` step 5, THREAT_MODEL.md T13): per
  world, hard ceilings on concurrent VM count, CPU/RAM, concurrent forks,
  wall-clock runtime, and spend/day. Enforced at task-admission time in the
  same non-LLM gate as target enforcement — an agent cannot negotiate past
  a quota by rephrasing a request, because the check reads counters from
  the registry, not claims from the request.
- **Teardown** (THREAT_MODEL.md T14): `range-runtime` records every
  provisioned resource ID in a durable ledger **before** reporting
  provisioning successful. Every range/world has a hard TTL set at
  creation. A reaper process, running independently of any specific task's
  completion path, reconciles the ledger against actual Vultr account state
  on a fixed interval and destroys anything past TTL or orphaned (present
  in the account, absent or stale in the ledger). Teardown revokes the
  range's CALDERA enrollment token and any range-ownership tokens scoped to
  it as part of the same operation, not as a separate best-effort step.
  Teardown is idempotent and retried on failure; a teardown that still
  fails after retries alerts a human rather than being silently dropped.

## 10. Summary: what a jailbroken agent can and cannot do

An agent that has been fully compromised by prompt injection — able to emit
arbitrary tool-call text, arbitrary parameters, arbitrary "reasoning" — is
constrained to:

- selecting among **pre-compiled** DAG task nodes and their **pre-declared**
  target sets and ability catalog entries;
- having every resulting request independently re-checked against a
  registry it cannot write to, by a service it cannot reach except through
  a fixed request schema;
- having any deny be a hard, audited, non-retryable-by-rewording failure;
- being physically unable to route a range VM's network traffic anywhere
  the VPC-level firewall doesn't already allow, regardless of what
  `authorize()` decides;
- being unable to read, exfiltrate, or forge the one class of credential
  (range-ownership token / execution-authorization ticket) that would let
  it act, because both are server-signed and it never holds the key.

It cannot mint a token, widen a target set, invent a new ability, approve
its own human-gated action, extend a TTL, or reach anything outside a
GhostRange-owned range — not because it has been asked not to, but because
none of those operations have a code path reachable from anything an agent
can say.
