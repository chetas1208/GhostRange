# Production Boundary

GhostRange and GhostGate **never** mutate production systems in M11.

## Forbidden operations (enforced in code reviews + `ProductionBoundaryGuard`)

- `terraform apply` / `tofu apply` against production state
- `kubectl apply` to production clusters
- SSH/exec to production hosts
- Deployment webhooks to external CD
- Creating `ApprovalDecisionV1` with `actor_kind=MODEL`

## Allowed

- Generate patches (Compose, Terraform text, K8s YAML) for **human review**
- Simulate apply/rollback in **disposable GhostRange worlds**
- Export `GhostPromotionBundleV1`
- Record human `ApprovalDecisionV1` bound to `change_candidate_hash`

## Language

Use: **READY FOR HUMAN REVIEW UNDER RECORDED POLICIES**

Not: **production-safe** or **deployed**
