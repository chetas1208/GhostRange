# Benchmark secrecy

- Active hidden scenarios: lifecycle `PRIVATE` / `ACTIVE`.
- Ground truth and hidden verifier specs live only under `evaluation/private/`.
- GhostEvolve training pipelines must not ingest active M19 hidden trajectories.
- Post-evaluation feedback to learners is **sanitized** (family/slice), never seed-specific thresholds.
