# GhostShield visualization (M17)

Primary tabs remain: **Multiverse**, **Execution**, **Evidence** — no Shield/Policy tab.

Execution scene:

- `<ActionGate />` — driven by `authorizationGate` in Zustand (worker REQUESTED/PROVISIONING/READY/FAILED).
- `<ActionPermit />` — geometric link while provisioning.

Evidence tab (future): show property id, assurance level (`MODEL_CHECKED`, `RUNTIME_ENFORCED`), last verdict — not “PROVEN SAFE”.

Components live in `packages/ui-3d/src/shield/`.
