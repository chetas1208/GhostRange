# GhostMesh Operations

## Enable sharing (explicit)

1. Edit `config/mesh-contribution-policy.yaml` — set `sharing_enabled: true` only after operator review.
2. Configure federation membership and node keys (production: mTLS/OIDC — not fully wired in M13 sim).
3. Run local harness: `ghostrange-ghostmesh` or `POST /v1/mesh/demo/story`.

## Kill switch

Set `sharing_enabled: false` — extraction may continue locally; publish endpoints reject.

## Labels

- `SIMULATED_MESH` — harness/API demo
- `LIVE_MESH_NOT_RUN` — no multi-Vultr federation in M13 baseline

## Benchmark

```bash
python scripts/benchmark_m13.py
```

Output: `artifacts/benchmarks/m13/summary.json`
