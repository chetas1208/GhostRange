# GhostEvolve ↔ GhostArena promotion gate

Production promotion (`PromotionLevel.PRODUCTION`) requires a current `GhostArenaReleaseReportV1` where `qualifies_promotion()` is true (`QUALIFIED` and no safety regression).

```python
gate.authorize_promotion(request, candidate, arena_report=report)
```

Missing or non-qualifying report → `GatewayError` with GhostArena recommendation.

GhostArena **does not** promote. GhostEvolve proposes; GhostShield authorizes execution.

Fields on `EvolutionPromotionRequestV1`: `arena_release_report_digest`, `arena_qualified` (optional hints; report is authoritative when passed).
