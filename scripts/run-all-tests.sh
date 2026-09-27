#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
make install-py
. .venv/bin/activate
pytest -q \
  packages/contracts/tests \
  packages/events/tests \
  --ignore=packages/events/tests/store \
  packages/evidence/tests \
  packages/range-compiler/tests \
  packages/scheduler/tests \
  packages/ghostledger/tests \
  packages/adversarial-verifier/tests \
  packages/ghostdirector/tests \
  packages/ghostgate/tests \
  packages/ghostwatch/tests \
  packages/execution-graph/tests \
  packages/adversary-adapter/tests \
  apps/api/tests
npm run typecheck
npm run test
echo "ALL TESTS PASS"
