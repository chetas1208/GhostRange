# ghostrange-policy-check

The concrete enforcement point `docs/security/EXECUTION_POLICY.md` designs
but does not, by itself, code. Owner: Agent 05 (Security Boundary
Engineer), added M2.

This is the M2 stand-in for the "separate deployable component" that doc's
§1 describes: `PolicyCheckService.authorize()` is real, callable,
in-process code today; wrapping it behind an internal RPC endpoint later
(per EXECUTION_POLICY.md §4's mTLS/no-agent-reachable-surface requirement)
does not change this package's public interface, so downstream callers
(execution-graph, adversary-adapter, range-runtime, vultr-control) can
build against it now without churn later.

## Install

```bash
pip install -e packages/contracts
pip install -e "packages/policy-check[dev]"
```

## Interface

```python
from datetime import timedelta
from ghostrange_contracts.enums import AbilityCategory, PolicyActorKind
from ghostrange_contracts.policy import ActorRef, ProvenanceRef
from ghostrange_policy_check import (
    PolicyCheckService, PolicyRegistry, TokenSigner, PolicyDenied,
)

# --- one-time setup (range-runtime's provisioning pipeline / bootstrap) ---
registry = PolicyRegistry()
registry.register_range(range_id, target_set)          # from real IaC apply output
registry.register_ability("attack.discovery.host")      # reviewed catalog onboarding
registry.set_quota(world_id, max_cost_usd)

signer = TokenSigner()  # reads GHOSTRANGE_POLICY_SIGNING_KEY (>=16 bytes); no implicit default key
token = signer.mint_token(
    world_id=world_id, range_id=range_id, target_set=target_set,
    capabilities=[AbilityCategory.RECON], ttl=timedelta(hours=1),
)

# --- per-request (execution-graph, at dispatch time) -----------------------
service = PolicyCheckService(registry, signer)
try:
    decision = service.authorize(
        request,             # ExecutionRequestV1
        token,                # RangeOwnershipTokenV1
        actor=ActorRef(kind=PolicyActorKind.AGENT, id=agent_id, tool_call_id=tool_call_id),
        provenance=ProvenanceRef(package="execution-graph", version=__version__, dag_node_id=node_id),
    )
except PolicyDenied as exc:
    # Hard fail the task node. exc.decision.reason is a PolicyDenyReason.
    # Never retry with different wording; never fall back to a degraded path.
    raise

# --- executor side (adversary-adapter / range-runtime / vultr-control) ----
# Independently re-verify BEFORE the side-effecting call -- defense in depth,
# not redundant paperwork: this still blocks a caller that skipped
# execution-graph/policy-check and called the executor directly.
assert signer.verify_ticket(decision.ticket, expected_request_hash=decision.request_hash)
```

**Every deny raises `PolicyDenied`.** There is no boolean return value a
caller could `if decision:` past by accident, and no "policy service
unreachable → assume allowed" branch: any unexpected exception inside
`authorize()` is itself converted into a `PolicyDenied` with reason
`POLICY_SERVICE_UNAVAILABLE`.

## What `authorize()` checks, in order

Mirrors `docs/security/EXECUTION_POLICY.md` §3.2 exactly:

1. Token signature valid, not expired, `world_id`/`range_id` match the request (else `BAD_TOKEN_SIGNATURE` / `TOKEN_EXPIRED` / `TOKEN_SCOPE_MISMATCH`).
2. Re-derive the range's canonical target set from the registry (never from the request's own claims) and check the requested targets are a subset (`UNKNOWN_RANGE` / `TARGET_NOT_IN_RANGE`).
3. Requested `action_category` is in the token's granted `capabilities` (`CAPABILITY_NOT_GRANTED`).
4. `ability_ref` is in the reviewed ability catalog (`ABILITY_NOT_IN_CATALOG`).
5. Per-world quota admits the request's `resource_cost` (`QUOTA_EXCEEDED`).
6. If `action_category` is in `registry.human_approval_required_categories`, an unexpired approval record for this exact request hash exists (`HUMAN_APPROVAL_REQUIRED`).
7. Absolute off-range re-check (redundant with #2 by construction — `OFF_RANGE_TARGET_ABSOLUTE_DENY` has no reachable ALLOW path).

Every outcome — ALLOW or DENY — is appended to `service.audit_log`
(`AuditLog`, hash-chained, `verify_chain()` checkable).

## The other three primitives this package ships

- **`ssrf_guard.assert_safe_egress_url` / `is_blocked_address`** — the
  concrete SSRF backstop for the B7 boundary (THREAT_MODEL.md T6). Blocks
  loopback/RFC1918/link-local (which covers `169.254.169.254`, the Vultr
  metadata endpoint, without a special case). Any control-plane code that
  must resolve a caller-influenced host/URL (chiefly range-runtime's
  mediated evidence-fetch proxy) must call this first.
- **`model_output_guard.resolve_target`** — the only sanctioned way model
  output becomes a `TargetRef`. A DAG node pre-declares a small alias
  vocabulary (`"target-0"`, or execution-graph's own stable aliases) at
  compile time; the agent may only select among those aliases. A raw
  IP/hostname string the model invents is never accepted, however
  plausible it looks — `resolve_target` raises `UnknownTargetAliasError`.
- **`secrets.redact_secrets`** — logging-side redaction backstop
  (EXECUTION_POLICY.md §6). `packages/vultr-control` and
  `packages/range-runtime` are empty as of this M2 pass (verified by
  direct inspection — nothing there could log a secret yet); once they
  exist, any dict-shaped log line derived from a secrets-manager
  response/request MUST be routed through this first.

## Storage caveat (read before trusting this in anything but tests/demo)

`PolicyRegistry` and `AuditLog` are in-memory and process-local. This is
enough to exercise the real security property (the registry, not the
caller's claims, is authoritative) in tests, but it is not the production
deployment EXECUTION_POLICY.md §4/§8 describes (Postgres, an
INSERT/SELECT-only DB role for the audit table, mTLS-only RPC access, no
agent-reachable admin surface). Do not wire a real, agent-facing execution
path to this in-memory instance without first replacing the storage layer.

## Tests

```bash
pytest packages/policy-check/tests
```

Includes the required negative tests: off-range target, expired token,
disallowed action type (capability not granted) — plus bad signature,
world/range spoofing, unknown range, unreviewed ability, quota exceeded,
and missing human approval, each asserted to actually raise `PolicyDenied`
with the matching `PolicyDenyReason`, not just documented as denied.
