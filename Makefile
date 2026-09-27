.PHONY: dev test demo golden-path live-golden install-py ui-acceptance prod-preflight prod-build prod-up prod-down prod-status prod-smoke prod-deploy prod-rollback

ROOT := $(shell pwd)
VENV := $(ROOT)/.venv

install-py:
	python3 -m venv $(VENV) 2>/dev/null || true
	. $(VENV)/bin/activate && pip install -q -U pip && pip install -q \
		-e packages/contracts[dev] -e packages/events[dev] \
		-e packages/range-compiler -e packages/range-runtime \
		-e packages/range-iac -e packages/vultr-control \
		-e packages/netbird-control \
		-e packages/cost -e packages/scheduler -e packages/evidence \
		-e packages/policy-check -e packages/ghostledger \
		-e packages/adversarial-verifier -e packages/ghostdirector \
		-e packages/execution-graph -e packages/adversary-adapter \
		-e apps/api[dev]

dev:
	npm run dev

test: install-py
	. $(VENV)/bin/activate && pytest -q --ignore=packages/events/tests/store packages/ghostdirector/tests packages/adversarial-verifier/tests \
		packages/ghostledger/tests packages/scheduler/tests packages/range-compiler/tests \
		packages/execution-graph/tests packages/adversary-adapter/tests \
		packages/netbird-control/tests packages/vultr-control/tests packages/range-runtime/tests \
		packages/cost/tests \
		apps/api/tests
	npm run typecheck
	npm run test

demo: install-py
	. $(VENV)/bin/activate && pytest -q apps/api/tests/test_golden_path_mock.py apps/api/tests/test_mock_m2_e2e.py
	@echo "Mock demo path: PASS (M2 E2E + M10 golden path)"

golden-path: install-py
	. $(VENV)/bin/activate && pytest -q apps/api/tests/test_golden_path_mock.py::test_golden_path_orchestrator_mock

ui-acceptance:
	bash scripts/m20-ui-acceptance.sh

live-golden: install-py
	@test "$$GHOSTRANGE_LIVE" = "true" -o "$$GHOSTRANGE_LIVE" = "1" || (echo "Set GHOSTRANGE_LIVE=true"; exit 1)
	. $(VENV)/bin/activate && echo "LIVE_GOLDEN_PATH_NOT_RUN_NO_CREDENTIALS unless VULTR_API_KEY set and orchestrator extended"

prod-preflight:
	bash scripts/deploy-preflight.sh .env.production

prod-build:
	docker compose -f docker-compose.prod.yml build

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-status:
	bash scripts/production-status.sh

prod-smoke:
	bash scripts/smoke-test-production.sh http://127.0.0.1

prod-deploy:
	bash scripts/deploy-vultr.sh

prod-rollback:
	@test -n "$(SHA)" || (echo "Usage: make prod-rollback SHA=<git-sha>"; exit 1)
	bash scripts/rollback-vultr.sh $(SHA)
