# GhostGate (M11)

Turns verified remediations into **human-reviewable production change packages**.

GhostGate does **not** deploy to production. See `docs/security/PRODUCTION_BOUNDARY.md`.

```bash
ghostrange-promotion prepare --experiment-id <uuid>
ghostrange-promotion inspect <candidate-id>
ghostrange-promotion export <candidate-id>
```
