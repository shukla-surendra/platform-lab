# Top-level Makefile — build/serve an MkDocs site for ANY folder in this monorepo.
#
# Usage:
#   make docs  FOLDER=cloud-practice   # one command: init (if needed) + serve
#   make serve FOLDER=cloud-practice   # live-reloading preview at http://127.0.0.1:8000
#   make build FOLDER=cloud-practice   # build the static site into <folder>/site/
#   make clean FOLDER=cloud-practice   # remove <folder>/site/
#   make init  FOLDER=k8s_mlops        # scaffold docs/ symlinks + a default mkdocs.yml
#
# Folders that already have their own hand-curated mkdocs.yml (engineering_fundamentals,
# k8s_explorer, genai_lab) are used as-is. For any other folder, run `make init` once —
# it symlinks that folder's markdown-bearing subdirectories into <folder>/docs/ (the same
# pattern engineering_fundamentals already uses) and writes a default mkdocs.yml with no
# explicit nav, so MkDocs auto-generates navigation from the directory tree.
#
# No global pip install and no per-folder venv/lockfile is needed: mkdocs + mkdocs-material
# + pymdown-extensions are resolved on the fly via `uv run --with`, isolated from whatever
# pyproject.toml/uv.lock that folder's own project may have (--no-project).
#
# `make run FILE=...` is separate: it uses the top-level uv project (root pyproject.toml,
# root .venv) to run a standalone script — e.g. one that lives directly under a repo-root
# folder like system_design_foundation/ rather than inside its own uv sub-project.

MKDOCS_DEPS := mkdocs mkdocs-material pymdown-extensions
UV_MKDOCS   := uv run --no-project $(foreach d,$(MKDOCS_DEPS),--with $(d)) mkdocs

.PHONY: help docs serve build clean init run _check-folder _require-mkdocs-yml _check-file

help:
	@echo "Usage: make <target> FOLDER=<folder-name>"
	@echo ""
	@echo "  make docs  FOLDER=<folder>  - one command: init (if needed) + serve"
	@echo "  make init  FOLDER=<folder>  - scaffold docs/ symlinks + a default mkdocs.yml"
	@echo "                                (skipped if that folder already has one)"
	@echo "  make serve FOLDER=<folder>  - live-reloading preview at http://127.0.0.1:8000"
	@echo "  make build FOLDER=<folder>  - build the static site into <folder>/site/"
	@echo "  make clean FOLDER=<folder>  - remove <folder>/site/"
	@echo ""
	@echo "Works on any top-level folder in this repo. mkdocs + mkdocs-material +"
	@echo "pymdown-extensions are resolved per-run via 'uv run --with' — nothing is"
	@echo "installed globally or persisted into the folder's own venv."
	@echo ""
	@echo "Example: make docs FOLDER=cloud-practice"
	@echo ""
	@echo "  make run FILE=<path/to/script.py>  - run a standalone script with the"
	@echo "                                        top-level uv venv (root pyproject.toml)"
	@echo ""
	@echo "Example: make run FILE=system_design_foundation/consistent_hashing/demo_consistent_hashing.py"

docs: init serve

_check-folder:
	@if [ -z "$(FOLDER)" ]; then \
		echo "FOLDER is required, e.g.: make serve FOLDER=cloud-practice"; exit 1; \
	fi
	@if [ ! -d "$(FOLDER)" ]; then \
		echo "No such folder: $(FOLDER)"; exit 1; \
	fi

init: _check-folder
	@if [ -f "$(FOLDER)/mkdocs.yml" ]; then \
		echo "$(FOLDER)/mkdocs.yml already exists — leaving it alone."; \
	else \
		bash scripts/mkdocs_init.sh "$(FOLDER)"; \
	fi

_require-mkdocs-yml: _check-folder
	@if [ ! -f "$(FOLDER)/mkdocs.yml" ]; then \
		echo "$(FOLDER) has no mkdocs.yml yet — run 'make init FOLDER=$(FOLDER)' first."; \
		exit 1; \
	fi

serve: _require-mkdocs-yml
	cd "$(FOLDER)" && $(UV_MKDOCS) serve -a 127.0.0.1:8000

build: _require-mkdocs-yml
	cd "$(FOLDER)" && $(UV_MKDOCS) build --strict

clean: _check-folder
	rm -rf "$(FOLDER)/site"

_check-file:
	@if [ -z "$(FILE)" ]; then \
		echo "FILE is required, e.g.: make run FILE=system_design_foundation/consistent_hashing/demo_consistent_hashing.py"; exit 1; \
	fi
	@if [ ! -f "$(FILE)" ]; then \
		echo "No such file: $(FILE)"; exit 1; \
	fi

run: _check-file
	uv run python "$(FILE)"
