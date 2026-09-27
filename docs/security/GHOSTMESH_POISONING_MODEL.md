# GhostMesh Poisoning Model

## Adversary

Malicious participant submits crafted knowledge to mislead others' Directors.

## Defenses (layered)

1. Schema + DLP + semantic checks
2. `detect_anomalies` / quarantine
3. Sybil quotas + membership allowlist
4. **Strongest:** local validation before any claim

## Benchmark

Node E smuggle string blocked at transform; coordinator rejects non-members.
