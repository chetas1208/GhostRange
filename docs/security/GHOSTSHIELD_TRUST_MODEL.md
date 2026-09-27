# GhostShieldTrustModelV1

See `GhostShieldTrustModelV1` in `ghostshield_m17.py`.

| Entity | Class |
|--------|-------|
| LLM | UNTRUSTED proposer |
| Director / Scheduler / Frontend | UNTRUSTED for authorization |
| Worker | SEMI_TRUSTED executor |
| Remote mesh | UNTRUSTED data |
| Policy engine + gateway | TRUSTED |
| Canonical Postgres | TRUSTED (integrity assumptions) |
| Provider API response | External observation, not policy authority |
