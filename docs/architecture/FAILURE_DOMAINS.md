# Failure Domains (M10)

| Domain | Example failure | Detection | Containment | Recovery | Cleanup |
|--------|-----------------|-----------|-------------|----------|---------|
| API | Process crash mid-run | health, run status | stop new runs | reconcile on boot | orphan scan |
| SSE | Client disconnect | heartbeat | none | replay from `after=` | — |
| DB | Postgres unavailable | connection errors | degrade to memory gateway | retry | — |
| Provider | 429/timeout | adapter errors | backoff | reconcile state | destroy owned IDs |
| World | health check fail | probe | mark world failed | prune branch | teardown |
| Worker | task death | task status | reschedule | scheduler fallback | release compute |
| Inference | timeout | HTTP client | skip model proposals | rule-based director | — |
| Director | exception | campaign FAILED | no new experiments | resume from checkpoint | — |
| Scheduler | plan error | empty plan | conservative serial plan | log reason | — |
| Ledger | sign fail | ATTESTATION_PENDING | continue run | local dev key | — |

Chaos matrix execution: Agent 36 (planned). Safe fallbacks: prompt §41.
