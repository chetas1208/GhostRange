# GhostRange — final integrated architecture (M20)

See flow diagram in M20 spec. Implementation anchor:

```text
POST /v1/campaigns/golden
  → RangeCompiler (compose file)
  → GhostDirectorSimulator (3 hypotheses, auth incident)
  → GhostScheduler V3 plan
  → Adversarial verification (auth lab)
  → GhostLedger seal + verify
  → GhostArena release report (sim)
  → GhostCampaignReportV1 + GhostEvidenceBundleV1 + ReproductionManifestV1
```

**GhostRuntime** wraps long-running execution in worker/API processes (not fully orchestrated in one HTTP call).

**GhostShield** wraps compute provider when configured (`build_compute_provider`).

**GhostEvolve** consumes experience after campaigns; promotion requires Arena report for PRODUCTION.

Legacy entry: `POST /v1/golden-path/runs` (M10) — still supported.

Canonical identity: **`campaign_id`** on `GhostCampaignV1` aligns with golden path `campaign_id`.

Event target envelope: `CanonicalEventEnvelopeV1` in contracts; durable store still uses legacy row shape with migration path documented in `packages/events`.
