# Usage:
#   make up            # start MongoDB (port 27018) and load the shop data
#   make list          # show the lesson scripts
#   make run L=03      # run lesson 03_*.js
#   make all           # run every lesson in order
#   make shell         # interactive mongosh on the "shop" database
#   make seed          # reload the data from scratch (fixes "odd" output)
#   make down          # stop and delete the container
#
# Scripts run INSIDE the container (mongosh isn't needed on the host); this folder is
# mounted there at /lab, see docker-compose.yml.

MONGOSH := docker compose exec -T mongo mongosh --quiet

.PHONY: help up seed list run all shell down

help:
	@sed -n '2,8p' Makefile | sed 's/^# //'

up:
	docker compose up -d --wait
	$(MONGOSH) /lab/seed.js

seed:
	$(MONGOSH) /lab/seed.js

list:
	@ls [0-9]*.js

run:
	@if [ -z "$(L)" ]; then echo "L is required, e.g.: make run L=03"; exit 1; fi
	@f=$$(ls $(L)_*.js 2>/dev/null | head -1); \
	if [ -z "$$f" ]; then echo "no lesson matching $(L)_*.js (try: make list)"; exit 1; fi; \
	echo "### $$f"; $(MONGOSH) /lab/$$f

all:
	@for f in [0-9]*.js; do echo "### $$f"; $(MONGOSH) /lab/$$f; echo; done

shell:
	docker compose exec mongo mongosh shop

down:
	docker compose down
