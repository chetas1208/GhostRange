# M16 reliability benchmark artifacts

Directories:

- `horizon/` — 5, 10, 20, 40, 80, 160 dependent-step campaigns (simulator)
- `process-crash/`, `vm-reboot/`, `postgres/`, `object-storage/`, `vultr-api/`, `worker/`, `network/`, `model/`
- `checkpoint/`, `replay/`, `orphans/`, `cost/`

Baselines: `NO_RECOVERY`, `RETRY_ONLY`, `RESTART_FROM_BEGINNING`, `CHECKPOINT_ONLY`, `GHOSTRUNTIME_V1`.

Label runs: `SIMULATED_CHAOS` vs `CONTROLLED_LIVE_CHAOS`.
