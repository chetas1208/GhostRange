# GhostMesh Privacy Model

## Leaves node (only when authorized)

Structurally abstracted tags, applicability profiles, provenance digests, privacy profiles, noisy aggregates.

## Stays local

Raw evidence, hostnames, credentials, topology, production telemetry, source code.

## Mechanisms

1. Field removal + generalization
2. Regex DLP (`dlp.py`)
3. Semantic leakage heuristics (`semantic_privacy.py`)
4. DP on counts only (`differential_privacy.py`)
5. Minimum cohort release gates

## Not guaranteed

Reconstruction resistance against a malicious coordinator with side information — see threat model.
