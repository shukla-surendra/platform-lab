PYTHON ?= .venv/bin/python
Q ?= What happens to backend work in FastAPI when a client disconnects, and how does FastAPI run under the hood?

.PHONY: install run langfuse-up langfuse-down clean

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.txt
	test -f .env || cp .env.example .env

run:
	$(PYTHON) agent.py "$(Q)" $(if $(THREAD),--thread $(THREAD))

# Self-hosted Langfuse v3 (web, worker, Postgres, ClickHouse, Redis, MinIO) from the official
# docker-compose. UI at http://localhost:3000: sign up, create a project, copy its API keys to .env.
langfuse-up:
	test -d langfuse-server || git clone --depth 1 https://github.com/langfuse/langfuse.git langfuse-server
	cd langfuse-server && docker compose up -d

langfuse-down:
	cd langfuse-server && docker compose down

clean:
	rm -rf output
