# GhostWatch operations

1. Complete M11 promotion + human approval (`change_candidate_hash` recorded).
2. External executor applies change (outside GhostRange).
3. Start GhostWatch campaign with matching artifact digests.
4. Default `OBSERVE_ONLY`; enable `PREAUTHORIZED_ROLLBACK` only with scoped adapter credentials.
5. Emergency: set `GHOSTWATCH_CONTROL_DISABLED=true` — observation may continue, control stops.

Local dev: `POST /v1/ghostwatch/simulate` or `ghostrange-ghostwatch simulate good-canary`.
