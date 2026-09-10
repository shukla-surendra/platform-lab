PYTHON ?= python3
COMPOSE ?= docker compose

.PHONY: install pull reset ingest ask fix daemon simulate tail-audit clean \
	docker-build docker-up docker-up-fg docker-down docker-restart docker-ps docker-logs \
	docker-logs-agent docker-logs-ops docker-logs-knowledge docker-logs-ollama \
	docker-ask docker-fix docker-simulate docker-reset docker-apply docker-dry-run \
	docker-shell docker-clean

install:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -q -r requirements.txt

pull:
	ollama pull qwen3.5:latest
	ollama pull qwen3-embedding:0.6b

reset:
	.venv/bin/python seed.py

ingest:
	.venv/bin/python rag/ingest.py

# make ask Q="why is fraud-detection showing degraded predictions?"
ask:
	.venv/bin/python agent_cli.py "$(Q)"

# make fix Q="checkout-api is throwing errors, please fix it"
fix:
	.venv/bin/python agent_cli.py --apply "$(Q)"

daemon:
	.venv/bin/python daemon.py

daemon-apply:
	.venv/bin/python daemon.py --apply

# make simulate SCENARIO=model-drift
simulate:
	.venv/bin/python events/simulate.py --scenario $(SCENARIO)

tail-audit:
	tail -f audit_log.jsonl

clean:
	rm -f world_state.json audit_log.jsonl agent_sessions.sqlite
	rm -rf faiss_index events/inbox/*.json events/processed/*.json events/failed/*.json

# --- Docker / production simulation ------------------------------------------------------------
# See README.md's "Docker / production simulation" section. Services: ollama, ollama-pull,
# ops-server, knowledge-server, agent (automode daemon), cli (one-shot commands, profile "tools").

docker-build:
	$(COMPOSE) build

# Starts ollama + both MCP servers + the automode agent, detached. First run also pulls both
# Ollama models and builds the FAISS index inside their containers -- expect it to take a while.
docker-up:
	$(COMPOSE) up -d --build

# Same, but attached -- see every service's logs interleaved in this terminal, Ctrl-C to stop
# (containers keep running; use docker-down to actually stop them).
docker-up-fg:
	$(COMPOSE) up --build

docker-down:
	$(COMPOSE) down

docker-restart:
	$(COMPOSE) restart

docker-ps:
	$(COMPOSE) ps

# make docker-logs [SERVICE=agent]
docker-logs:
	$(COMPOSE) logs -f --tail=200 $(SERVICE)

docker-logs-agent:
	$(COMPOSE) logs -f --tail=200 agent

docker-logs-ops:
	$(COMPOSE) logs -f --tail=200 ops-server

docker-logs-knowledge:
	$(COMPOSE) logs -f --tail=200 knowledge-server

docker-logs-ollama:
	$(COMPOSE) logs -f --tail=200 ollama

# make docker-ask Q="why is fraud-detection showing degraded predictions?"
docker-ask:
	$(COMPOSE) run --rm cli python agent_cli.py "$(Q)"

# --apply is a no-op against a running compose stack -- the dry-run gate is fixed by ops-server's
# own APPLY_CHANGES env var. This target exists as a clear error message pointing at docker-apply.
docker-fix:
	@echo "docker compose runs ops-server with a fixed APPLY_CHANGES -- 'make docker-ask' can't"
	@echo "override it per-request. Use 'make docker-apply' to restart ops-server in apply mode,"
	@echo "then 'make docker-ask Q=...' as usual; 'make docker-dry-run' switches back."
	@exit 1

# make docker-simulate SCENARIO=model-drift
docker-simulate:
	$(COMPOSE) run --rm cli python events/simulate.py --scenario $(SCENARIO)

docker-reset:
	$(COMPOSE) run --rm cli python seed.py

# Restart ops-server with APPLY_CHANGES=true -- mutating tools actually execute until you switch
# back with docker-dry-run. Ticket/world state persists across this restart (see
# docker/ops_entrypoint.sh); only the dry-run gate changes.
docker-apply:
	APPLY_CHANGES=true $(COMPOSE) up -d --force-recreate ops-server

docker-dry-run:
	APPLY_CHANGES=false $(COMPOSE) up -d --force-recreate ops-server

# make docker-shell [SERVICE=cli]
docker-shell:
	$(COMPOSE) run --rm $(or $(SERVICE),cli) sh

# Stop everything and delete the named volumes (Ollama models + world_state.json/faiss_index) --
# next docker-up starts completely fresh, including re-pulling both models.
docker-clean:
	$(COMPOSE) down -v
