PYTHON ?= python3

.PHONY: docs-install docs docs-serve docs-clean

docs-install:
	$(PYTHON) -m pip install -q -r requirements-docs.txt

docs: docs-install
	$(PYTHON) -m mkdocs build --strict
	$(PYTHON) -m mkdocs serve

docs-build: docs-install
	$(PYTHON) -m mkdocs build --strict

docs-serve: docs-install
	$(PYTHON) -m mkdocs serve

docs-clean:
	rm -rf site
