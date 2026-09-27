# M17 formal assurance results

| Property | Checker | Result | States | Notes |
|----------|---------|--------|--------|-------|
| `NeverExceedMax` | TLC | **NOT RUN** | — | TLC not installed in dev shell; spec in `formal/m17/WorkerFleet.tla` |

**Counterexamples:** none preserved.

**Implementation bug from formal:** none found (no counterexample yet).

**Next:** run `tlc -config WorkerFleet.cfg WorkerFleet.tla` in local CI; extend model with permits + stale execution.
