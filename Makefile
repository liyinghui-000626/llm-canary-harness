COMPOSE_FILE := docker-compose.milvus.yml

.PHONY: milvus-up milvus-down local-flow local-flow-up local-flow-stop smoke-test

milvus-up:
	docker compose -f $(COMPOSE_FILE) up -d

milvus-down:
	docker compose -f $(COMPOSE_FILE) down

local-flow:
	bash scripts/run_local_milvus_flow.sh

local-flow-up:
	SKIP_SMOKE=1 KEEP_SERVICES_UP=1 KEEP_MILVUS_UP=1 bash scripts/run_local_milvus_flow.sh

local-flow-stop:
	@if [ -f .run/admin.pid ]; then kill "$$(cat .run/admin.pid)" >/dev/null 2>&1 || true; rm -f .run/admin.pid; fi
	@if [ -f .run/gateway.pid ]; then kill "$$(cat .run/gateway.pid)" >/dev/null 2>&1 || true; rm -f .run/gateway.pid; fi
	@rm -f .run/local-flow.env

smoke-test:
	python3 scripts/smoke_test_canary.py
