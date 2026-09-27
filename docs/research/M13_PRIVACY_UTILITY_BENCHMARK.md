# M13 Privacy / Utility Benchmark

Run: `python scripts/benchmark_m13.py` → `artifacts/benchmarks/m13/summary.json`

## Corpus

Synthetic tenants A–E in `GhostMeshHarness` (not live Vultr).

## Initial results (simulated)

| Metric | Observation |
|--------|-------------|
| Utility (B) | Mesh prior moves `session_refresh_identity_probe` before broad scan |
| Negative transfer (C) | Local validation rejects misleading prior |
| Privacy proxy | Published contribution tags exclude hostnames from A raw ledger |
| Poison (E) | Smuggled execution string blocked at privacy transform |

## Not claimed

Formal DP guarantees, secure aggregation benefits, or live multi-tenant reconstruction attack resistance — **benchmark honesty required**.
