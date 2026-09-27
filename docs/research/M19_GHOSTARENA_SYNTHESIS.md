# M19 GhostArena — evaluation research synthesis (anchors)

## AgentCyberRange

- **Task model:** Multi-host cyber tasks with tool use in isolated ranges.
- **Environment:** Reproducible range templates, parallel trials.
- **Verifier:** Explicit result verification, matched budgets.
- **GhostRange translation:** GhostArena targets **defensive investigation/remediation**, not unrestricted attack autonomy. Adopt isolated multi-step ranges + verification; reject copying unrestricted attack benchmarks.

## AgencyBench

- **Horizon:** Long, realistic workflows; many tool calls; large context.
- **Metrics:** Functional/rubric verification, efficiency, self-correction.
- **GhostRange translation:** Adopt long-horizon + process scoring; reject sole reliance on final-answer LLM judge.

## DeepPlanning

- **Horizon:** Constrained long-horizon planning.
- **GhostRange translation:** Adopt dependency-depth control separate from step count; use in scheduler/generalization suites.

## Long-horizon failure localization (2024–2026 trajectory literature)

- **Finding:** Final success can mask corruption or fabricated intermediate success.
- **GhostRange translation:** `FailureLocalizationV1`, process verifier, `SUCCESS_WITH_POLICY_VIOLATION` ≠ pass.

## Production agent evaluation frameworks

- **Pattern:** Tiered eval (smoke → full), version pinning, cost normalization.
- **GhostRange translation:** `Evaluation tiers` in roadmap; `GhostArenaReleaseReportV1` with cost deltas.

## Threat-oriented digital twin evaluation (2026 methodology themes)

- **Pattern:** Reproducible security experiments, trust boundaries, hold-safe behavior.
- **GhostRange translation:** Sealed ranges in UI; GhostShield traps in safety suite.

### What we adopt

- Hidden holdout, paired baseline/candidate, process + outcome verification, anti-Goodhart traps, independent gate before promotion.

### What we reject

- Single leaderboard score, training on active hidden tests, LLM-as-sole safety verifier, mixing sim and live results without labels.

### What we must not claim

- "Generalizes" without hidden suite evidence.
- "Safe" from final task pass alone.
- Statistical superiority from one stochastic seed.

*(Full bibliographic URLs to be expanded in M20 literature pass; methodology above governs M19 implementation.)*
