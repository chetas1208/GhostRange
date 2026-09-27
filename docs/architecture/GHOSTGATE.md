# GhostGate (M11)

GhostGate sits between **GhostRange experimentation** and **human-controlled production change**.

## Does

- Build `ProductionChangeCandidateV1` from verified experiment context
- Generate **review-only** patches (Compose / Terraform snippet / config)
- Compare **tested twin delta** vs **proposed production delta** (`ChangeEquivalenceReportV1`)
- Run dimensional **PromotionReadinessV1** gates (claims, drift, fidelity, adversarial, rollback, observability)
- Recommend **DeploymentStrategyV1** / **CanaryPlanV1** (plans, not execution)
- Test rollback and post-change verification **in disposable worlds** (simulation status)
- Create **ApprovalRequestV1** bound to `change_candidate_hash`
- Export **GhostPromotionBundleV1** for CI / human review

## Refuses

- Production SSH, `terraform apply`, `kubectl apply`, deployment webhooks
- Model-created human approvals
- Treating **APPROVED** as **DEPLOYED**

See `docs/security/PRODUCTION_BOUNDARY.md` and `packages/ghostgate/ghostrange_ghostgate/boundary.py`.

## API

- `POST /v1/promotion/prepare`
- `GET /v1/promotion/candidates/{id}`
- `GET /v1/promotion/candidates/{id}/export`
- `POST /v1/promotion/candidates/{id}/approve` (human `approver_id`)
