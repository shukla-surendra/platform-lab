# Usage:
#   make up          # start MongoDB (27019)
#   make run L=02    # run 02_*.py
#   make all         # run all 5 in order
#   make down        # stop it
#
# Python deps are installed on the fly by uv (pymongo); no venv to manage.

PY := uv run -q --no-project --with-requirements requirements.txt python

.PHONY: help up run all down

help:
	@sed -n '2,5p' Makefile | sed 's/^# //'

up:
	docker compose up -d --wait

run:
	@if [ -z "$(L)" ]; then echo "L is required, e.g.: make run L=02"; exit 1; fi
	@f=$$(ls $(L)_*.py 2>/dev/null | head -1); \
	if [ -z "$$f" ]; then echo "no script matching $(L)_*.py"; exit 1; fi; \
	echo "### $$f"; $(PY) $$f

all:
	@for f in [0-9]*.py; do echo "### $$f"; $(PY) $$f; echo; done

down:
	docker compose down
