PYTHON ?= python3

.PHONY: install server-scratch client-scratch demo-scratch server-package client-package demo-package diff clean

install:
	$(PYTHON) -m pip install -r requirements.txt

server-scratch:
	cd from_scratch && $(PYTHON) server.py

client-scratch:
	cd from_scratch && $(PYTHON) client.py

# Starts a server, runs its client demo against it, and guarantees shutdown via run_demo.sh's
# trap -- the quickest way to see the whole thing work without two terminals.
demo-scratch:
	./run_demo.sh from_scratch 9100

server-package:
	cd with_package && $(PYTHON) server.py

client-package:
	cd with_package && $(PYTHON) client.py

demo-package:
	./run_demo.sh with_package 9101

diff:
	@echo "--- server.py ---"; diff -u from_scratch/server.py with_package/server.py || true
	@echo "--- client.py ---"; diff -u from_scratch/client.py with_package/client.py || true

clean:
	find . -name '__pycache__' -type d -exec rm -rf {} +
