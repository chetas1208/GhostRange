# Range Network Boundary — `ghostrange-auth-lab-v1`

Owner: Agent 05 (Security Boundary Engineer), M2. Companion documents:
`THREAT_MODEL.md` (T1-T17, especially T3/T5/T6/T9), `EXECUTION_POLICY.md`
(the `authorize()` mechanism), `docs/research/VULTR.md` (the FACT/OUR-
INTERPRETATION source this document's claims are checked against), and
ADR-006 (Vultr integration scope).

This document is scoped to exactly one concrete artifact: the network
boundary around `ranges/ghostrange-auth-lab-v1`, GhostRange's first real
range. It is deliberately narrower than THREAT_MODEL.md/EXECUTION_POLICY.md
(which describe the general architecture for any range/world) — its job is
to say, for THIS range, precisely what can reach what, what is confirmed
Vultr capability versus what is this project's own design choice on top of
it, and where the M1-era design's language overstated what a real Vultr
account can currently deliver. `ranges/ghostrange-auth-lab-v1/` itself is
owned by Agent 03 (provisioning/IaC) and Agent 06 (wave 2, the controlled
scenario content — which specific vulnerable service(s) it runs); this
document constrains what THEIR compiled infrastructure is allowed to do at
the network layer, independent of which CVE/scenario they choose.

## 0. One-paragraph summary

`ghostrange-auth-lab-v1`'s instances get no public IPv4 address and no NAT
gateway attached — this is the confirmed-capability mechanism that makes
"cannot reach the public internet" true regardless of any firewall rule.
They live in one Vultr VPC 2.0 network that, per Vultr's own documented
behavior, cannot exchange traffic with any other VPC 2.0 network — this is
the confirmed-capability mechanism that makes "cannot reach another
GhostRange world" true. The ONE thing range instances must be able to do —
report evidence/events back to the control plane — is not a punched-hole
egress rule on an otherwise-isolated network (see §3 for why that framing,
used in EXECUTION_POLICY.md §5, does not actually hold given how Vultr VPC
2.0 works); it is a same-VPC hop to a narrow relay that is the only thing
dual-homed between this range and the control plane. What remains
imperfect, stated plainly rather than assumed away: Vultr Firewall Groups'
egress-filtering capability is not confirmed by this project's own research
(§4.1), so this design does not rely on it for the primary "can't reach the
Internet" property; and the relay is a real, if narrow, residual attack
surface for a compromised range instance (§4.2).

## 1. What `ghostrange-auth-lab-v1` CAN reach

### 1.1 Its own VPC peers

Every asset instance provisioned for this range joins exactly one Vultr
VPC 2.0 network, `vpc_ids: [<this range's VPC id>]` (ADR-006's field
mapping). Instances in this VPC can reach each other over the private
`v4_subnet` Vultr assigns — this is the intended, in-scenario topology
(e.g. a vulnerable auth-service target and whatever CALDERA agent
(Sandcat) presence sits alongside it), further narrowed by per-asset
Firewall Group rules compiled from the RangeSpec's declared reachability
edges (ADR-006 §"VPC 2.0 as the safety-boundary unit"; Agent 06 owns the
exact edge list for this scenario's content).

### 1.2 The evidence/event callback relay — and why it is same-VPC, not cross-VPC

EXECUTION_POLICY.md §5 and THREAT_MODEL.md's diagram describe range egress
as "the only allowed rule is outbound-from-range to the CALDERA server's
control-plane callback port," phrased as a single hole punched through an
otherwise-isolated boundary between the range's VPC and the control-plane's
VPC. **That phrasing does not survive contact with Vultr's actual VPC 2.0
behavior** (confirmed FACT, `docs/research/VULTR.md` §5): separate VPC 2.0
networks cannot pass traffic to each other at all — no peering, full stop.
A firewall *rule* cannot open a route that the network fabric itself does
not provide; there is nothing for such a rule to point at.

The concrete resolution for `ghostrange-auth-lab-v1`: the evidence/event
callback endpoint range instances talk to is a **narrow relay component
that is itself a member of this range's own VPC 2.0** (in addition to
whatever separate interface it uses to reach the real control plane). From
inside the range, reaching the relay is an ordinary same-VPC hop — no
cross-VPC route, no public exposure of range instances, and no
egress-firewall-rule dependency at all for this path. The relay:

- accepts only schema-validated, evidence/event-shaped payloads (never
  arbitrary bytes/commands) from range instances on one narrow port,
  enforced by a Firewall Group rule scoped to that port and to this VPC's
  subnet as the allowed source;
- holds no Vultr API key, no CALDERA admin/operator credential, no DB
  credential — the same custody rule T4/§6 already require, restated here
  because the relay is a new component this document is introducing, not
  something EXECUTION_POLICY.md's existing text already covered;
- is the only thing dual-homed between a range's VPC and anything
  control-plane-adjacent; the deeper control-plane VPC holding the actual
  Vultr/DB/CALDERA-admin secrets is never itself VPC-joined to any range.

This is a genuine refinement of the M1-era design, not a weakening of it:
the isolation property THREAT_MODEL T3/T9 actually want ("a range cannot
reach the control plane's secrets") still holds — it now holds because the
relay is credential-free and the secrets-holding VPC is never in the same
network as any range, rather than because of a firewall rule whose
cross-VPC target was never reachable in the first place.

### 1.3 Its own metadata endpoint (self-query only)

Every Vultr instance, including range instances, can query
`169.254.169.254` unauthenticated (confirmed FACT, VULTR.md §4) — this is
how cloud-init retrieves the `user_data` supplied at creation, and it
cannot be firewalled off without breaking normal instance boot. This is
accepted, not a boundary gap: per §6 of EXECUTION_POLICY.md, `user_data`
for range instances never contains a secret-typed field, so a range
instance (or anything running on it, including a compromised process)
reading its own metadata learns nothing more sensitive than what it
already had (its own instance id, plan, network config, and its
non-secret cloud-init config). This is distinct from — and does not
license — the control-plane-side SSRF concern in §2.3 below.

## 2. What `ghostrange-auth-lab-v1` CANNOT reach

### 2.1 The public Internet, by default

Enforced by a confirmed Vultr capability, not a firewall rule: range
instances are created with `disable_public_ipv4: true` and no
`vpc_only`+NAT-gateway pairing that would grant one anyway (VULTR.md §4's
field list: `vpc_only` "requires a NAT gateway" to reach anything external
at all). No NAT gateway is provisioned for this range. An instance with no
public IPv4 and no NAT path has no Internet-routable interface, full stop
— this holds regardless of what any Firewall Group rule says, which is
precisely why §4.1 below matters: it is the mechanism this design actually
depends on, in place of an egress-filtering capability that is not
confirmed to exist.

**Range-iac compiler obligation this document is placing on Agent
03/06's build for this range** (a concrete, checkable claim, not a
prose promise): a unit/compiler test on `ghostrange-auth-lab-v1`'s
generated OpenTofu should assert every `vultr_instance` resource sets
`disable_public_ipv4 = true` and that no `vultr_instance` in this range
carries a `reserved_ip_id`/NAT-gateway attachment. If range-iac's test
suite doesn't yet have this assertion, it should before this range is
provisioned against a live account.

### 2.2 Other GhostRange worlds' VPCs

Confirmed FACT (VULTR.md §5): "VPC 2.0 networks are private even from
each other... your VPC 2.0s cannot pass traffic to each other." Every
world forked from `ghostrange-auth-lab-v1`'s root World gets its own
fresh VPC 2.0 (ADR-006, Decisions.md #12's golden-snapshot fork model) —
this is the strongest isolation guarantee this document can make, because
it is a network-fabric property Vultr states outright, not a rule GhostRange
configured and could misconfigure. See §4.3 for the one caveat (undocumented
per-account VPC count ceiling).

### 2.3 Cloud metadata endpoints, from control-plane code

This is the B7/T6 boundary (THREAT_MODEL.md), and it is about
control-plane code, not the range instance's own self-query (§1.3, which
is normal and unavoidable). No control-plane package (`vultr-control`,
`range-runtime`, `adversary-adapter`, `apps/api`) may construct an HTTP
call to a host derived from agent output or range-reported content without
first passing it through `packages/policy-check`'s
`ssrf_guard.assert_safe_egress_url` (implemented this M2 pass — see
§5). That guard blocks link-local space outright, which covers
`169.254.169.254` (and every other major cloud's metadata IP, since they
all use link-local) without needing a special case. `vultr-control`'s own
calls to the real Vultr API use a fixed, config-sourced base URL and never
touch this guard at all, by construction (T6's primary mitigation) — the
guard exists for the one legitimate case where control-plane code resolves
a caller-influenced host: the relay described in §1.2 and any future
mediated evidence-fetch path.

## 3. Why the "one egress hole" framing in EXECUTION_POLICY.md §5 needs a correction

Flagging this explicitly rather than quietly patching around it: prior to
this M2 pass, EXECUTION_POLICY.md §5 and THREAT_MODEL.md's ASCII diagram
described range egress as a single allow-rule from the range's VPC to the
CALDERA server, worded as if that VPC boundary were otherwise a normal
firewalled network where one rule opens one hole. Vultr VPC 2.0's actual,
documented behavior (no cross-VPC traffic, ever, no peering) means that
framing describes something Vultr's account-level networking does not
support as stated. This is exactly the kind of gap this document exists to
surface rather than let stand unexamined: the *intent* (range talks to
exactly one control-plane-side endpoint, nothing else) is preserved and, if
anything, strengthened by §1.2's relay design (same-VPC reachability
instead of a cross-VPC rule that was never actually enforceable); what
changes is the *mechanism*, and `EXECUTION_POLICY.md` §5 has been updated
(see that file's changelog note) to reference this document instead of
re-asserting the old framing.

## 4. What remains imperfect for M2, and why

Stated as specifically as the underlying research supports, per this
document's mandate not to overstate isolation strength.

### 4.1 Vultr Firewall Group egress-filtering capability is NOT confirmed

`docs/research/VULTR.md` §5 documents Firewall Group rule fields
(`ip_type`, `protocol`, `port`, `source`) from the Terraform/Pulumi
resource schema. Every field name there is INGRESS-shaped (`source` — the
address traffic is *coming from*); the research this project has actually
done does not confirm that Vultr Firewall Groups support outbound
(egress) rules at all, and VULTR.md does not flag this either way with a
NEEDS VERIFICATION marker — it is simply untested. This matters because
THREAT_MODEL.md T3 and EXECUTION_POLICY.md §5 were written as if
"default-deny egress, one allow-rule" were straightforwardly available as
a Firewall Group capability.

**What this design actually relies on instead (§2.1/§1.2), so this gap
does not silently become a real hole:** the no-public-IP/no-NAT-gateway
combination, which IS confirmed capability, not a firewall rule. Firewall
Groups are still used in this design (§1.1/§1.2), but only for their
confirmed capability (ingress filtering by source/port within the VPC),
never as the thing standing between a range instance and the public
Internet. **Action item, not yet done:** a live-account smoke test
(gated, manual, per VULTR.md's own testing convention) that attempts to
attach an actual outbound rule to a Vultr Firewall Group and observes
whether it has any effect, before any future document asserts Firewall
Group egress control as fact.

### 4.2 The relay (§1.2) is a real, narrow, residual attack surface

Introducing a same-VPC relay to solve §3's cross-VPC problem means a
compromised range instance CAN reach that relay — that is the one
intended hole, same category as THREAT_MODEL.md §4.1(e)'s already-flagged
"CALDERA server itself is reachable" residual risk. Mitigated by: the
relay holds no credentials (§1.2), accepts only schema-validated
evidence/event payloads (never arbitrary commands), and — same as the
existing CALDERA-server residual-risk note — needs its own hardening pass
(patch/version pinning, minimal exposed surface, rate limiting) that is
out of scope for this document beyond flagging it.

### 4.3 Per-account VPC 2.0 limits are unconfirmed at scale

VULTR.md §5 flags (NEEDS VERIFICATION) whether legacy "VPC" (gen 1) is
still provisionable, but does not check an exact per-account VPC 2.0 count
ceiling. `ghostrange-auth-lab-v1` alone, plus a modest number of forked
worlds, is very unlikely to hit any real-world Vultr account cap — this is
flagged for when GhostRange's fork count grows, not as a live M2 concern.
If a cap is ever hit, the fallback (a shared VPC with subnet-level
isolation) is a materially weaker guarantee than "Vultr says these
networks cannot talk to each other at all" and would need its own document
update, not a silent substitution.

### 4.4 This document's own enforcement code is a stub, not a production deployment

`packages/policy-check` (§5) is real, tested code, but its registry and
audit log are in-memory and process-local (see that package's README
"Storage caveat"). The network-layer protections in §1-§2 do not depend on
policy-check's storage backend at all — they hold at the Vultr account
level regardless of what's running in application code — but the
*application-layer* backstop (T5's "policy-check independently re-derives
the canonical target set") is only as durable as that in-memory registry
today. Do not treat this as production-ready defense in depth until the
registry/audit-log storage described in EXECUTION_POLICY.md §4/§8 (Postgres,
append-only DB grant) actually exists.

## 5. Enforcement code delivered this M2 pass (for cross-reference)

The concrete, testable primitives this document's claims lean on now exist
in code, not only in design prose:

- `packages/contracts/ghostrange_contracts/policy.py` — `TargetRef`,
  `RangeOwnershipTokenV1`, `ExecutionRequestV1`, `ExecutionTicketV1`,
  `PolicyDecisionV1`, `ActorRef`, `ProvenanceRef`, `AuditRecordV1` (additive
  to the existing `PolicyV1`/`BudgetV1`).
- `packages/policy-check/` (new package) — `PolicyCheckService.authorize()`
  implementing EXECUTION_POLICY.md §3.2's seven checks with hard-fail
  (`PolicyDenied`) semantics; `PolicyRegistry` (the re-derivation source of
  truth); `TokenSigner` (HMAC-based token/ticket mint+verify); `AuditLog`
  (hash-chained); `ssrf_guard` (§2.3's mandatory pre-flight check);
  `model_output_guard.resolve_target` (the only sanctioned model-output→
  target path — see §6); `secrets.redact_secrets` (logging backstop).
- Negative tests exist and pass for: off-range target, expired token,
  disallowed action category, bad token signature, world/range token
  spoofing, unknown/torn-down range, unreviewed ability, quota exceeded,
  missing human approval — `packages/policy-check/tests/`.

Full interface documented in `packages/policy-check/README.md`; that
document, not this one, is the source of truth for how Agent 07
(execution harness) and Agent 04 (range runtime) should call into it.

## 6. Arbitrary-target injection via model output

Restated here because it is a network-boundary-adjacent property (it is
what stops a compromised/adversarial agent from ever getting a
network-layer action pointed somewhere this document didn't already
enumerate): a DAG node pre-declares a small alias vocabulary for the
targets it may touch (e.g. `"target-0"`), populated only from
`ghostrange-auth-lab-v1`'s real, just-provisioned member list. Model
output may only select among those aliases —
`ghostrange_policy_check.model_output_guard.resolve_target` is the single
code path by which an alias becomes a real `TargetRef`, and it raises on
anything else, including a raw IP/hostname the model invents itself. This
means even a fully agent-controlled tool call cannot name a target this
document's §1/§2 boundaries were not already built around.
