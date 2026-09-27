# GhostRange Operations (M10 draft)

## Local dev

```bash
make install-py
make dev          # frontend
make api          # npm script → ghostrange-api (separate terminal)
```

## Tests

```bash
make test         # Python core + web typecheck/unit
make demo         # Mock M2 E2E + M10 golden path
make golden-path  # Golden path unit only
```

## Mock golden path (no cloud)

```bash
curl -X POST http://127.0.0.1:8000/v1/golden-path/runs
scripts/m20-golden-path.sh   # M20 report + Arena + evidence bundle
```

Returns phases: compile → director → scheduler → adversarial → ledger → teardown.

## M20 release check (no cloud spend)

```bash
scripts/m20-release-check.sh
```

Optional live: `RUN_M20_LIVE_CHECKS=true scripts/m20-release-check.sh`

## Live golden path

Requires **all**:

- `GHOSTRANGE_LIVE=true`
- `VULTR_API_KEY`
- `scripts/live_resource_lease.py` (single integration owner)

If credentials absent, label runs **`LIVE_GOLDEN_PATH_NOT_RUN_NO_CREDENTIALS`**.

## Orphan recovery

```bash
ghostrange-reconcile  # when configured for provider
```

## Emergency

Do not run destructive provider cleanup without confirming resource log (`artifacts/m10-live/resources.json` when live run exists).
