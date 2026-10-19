PYTHON ?= python3

.PHONY: up down logs install demo ingest search ask clean

up:
	docker compose up -d
	@echo "Waiting for Qdrant to be healthy..."
	@until [ "$$(docker inspect -f '{{.State.Health.Status}}' qdrant_vector_db 2>/dev/null)" = "healthy" ]; do sleep 1; done
	@echo "Qdrant is up on http://localhost:6333 (dashboard at /dashboard)."

down:
	docker compose down

logs:
	docker compose logs -f

install:
	$(PYTHON) -m pip install -r requirements.txt

demo:
	$(PYTHON) lifecycle_demo.py

ingest:
	$(PYTHON) ingest.py

search:
	$(PYTHON) search.py "$(Q)"

ask:
	$(PYTHON) rag.py "$(Q)"

clean:
	docker compose down -v
