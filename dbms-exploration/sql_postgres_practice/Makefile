# Usage:
#   docker compose up -d              # start Postgres once, first
#   make list                         # show available fixtures
#   make load  FIXTURE=ecommerce      # create the DB (if needed) + load schema.sql + seed.sql
#   make psql  FIXTURE=ecommerce      # open a psql shell against it
#   make reset FIXTURE=ecommerce      # drop and re-load from scratch
#   make load-all                     # load every fixture in fixtures/
#
# FIXTURE is matched against fixtures/NN_<fixture>/ (the numeric prefix is
# just for reading-order in a file listing -- the database itself is named
# without it, e.g. FIXTURE=ecommerce -> fixtures/01_ecommerce/ -> database "ecommerce").

DC := docker compose exec -T postgres

.PHONY: help list load psql reset load-all _check-fixture _find-dir

help:
	@echo "Usage: make <target> FIXTURE=<name>"
	@echo ""
	@echo "  make list                    - show available fixtures"
	@echo "  make load  FIXTURE=ecommerce - create DB (if needed) + load schema.sql + seed.sql"
	@echo "  make psql  FIXTURE=ecommerce - open a psql shell against it"
	@echo "  make reset FIXTURE=ecommerce - drop and re-load from scratch"
	@echo "  make load-all                - load every fixture in fixtures/"

list:
	@for d in fixtures/*/; do echo "  $$(basename $$d | sed 's/^[0-9]*_//')"; done

_check-fixture:
	@if [ -z "$(FIXTURE)" ]; then echo "FIXTURE is required, e.g.: make load FIXTURE=ecommerce"; exit 1; fi

_find-dir: _check-fixture
	@dir=$$(ls -d fixtures/*_$(FIXTURE) 2>/dev/null | head -1); \
	if [ -z "$$dir" ]; then echo "No fixture matching '$(FIXTURE)' under fixtures/"; exit 1; fi

load: _find-dir
	@dir=$$(ls -d fixtures/*_$(FIXTURE) 2>/dev/null | head -1); \
	echo "Loading $$dir -> database \"$(FIXTURE)\""; \
	$(DC) psql -U practice -d practice -tc "SELECT 1 FROM pg_database WHERE datname = '$(FIXTURE)'" | grep -q 1 \
		|| $(DC) createdb -U practice $(FIXTURE); \
	cat $$dir/schema.sql | $(DC) psql -U practice -d $(FIXTURE) -v ON_ERROR_STOP=1; \
	cat $$dir/seed.sql   | $(DC) psql -U practice -d $(FIXTURE) -v ON_ERROR_STOP=1; \
	echo "Loaded."

psql: _check-fixture
	$(DC) psql -U practice -d $(FIXTURE)

reset: _find-dir
	@$(DC) dropdb -U practice --if-exists $(FIXTURE)
	@$(MAKE) --no-print-directory load FIXTURE=$(FIXTURE)

load-all:
	@for d in fixtures/*/; do \
		name=$$(basename $$d | sed 's/^[0-9]*_//'); \
		$(MAKE) --no-print-directory load FIXTURE=$$name; \
	done
