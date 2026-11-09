PYTHON := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
# Cross-platform (macOS/Linux) LAN IP lookup: opens a UDP "connection" (no packets actually
# sent) to a public IP just to ask the OS which local interface/address it would route
# through - avoids branching on ifconfig (mac/BSD) vs ip (linux) output formats.
LAN_IP := $(shell $(PYTHON) -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>/dev/null)

# Run mkdocs through uv with its deps resolved per-run, so it works no matter which venv is
# active (e.g. the platform-lab root .venv, which doesn't ship mkdocs). Falls back to the
# local interpreter if uv isn't installed.
MKDOCS := $(shell command -v uv >/dev/null 2>&1 && echo "uv run --no-project --with mkdocs --with mkdocs-material --with pymdown-extensions mkdocs" || echo "$(PYTHON) -m mkdocs")

.PHONY: docs check ip

ip: ## Print this machine's LAN IP (what other machines on the network should use)
	@echo "$(LAN_IP)"

docs: ## Serve the MkDocs Material site at http://0.0.0.0:8000 (reachable from other machines on the network; live-reloads on edits to the real .md files)
	$(PYTHON) scripts/link_mkdocs_docs.py
	@echo "$(LAN_IP)"
	@echo "Serving at http://localhost:8000  (on the network: http://$(LAN_IP):8000)"
	$(MKDOCS) serve -a 0.0.0.0:8000

check: ## Validate all relative Markdown links, then build the MkDocs site (no serve) - CI-friendly
	$(PYTHON) scripts/check_links.py
	$(PYTHON) scripts/link_mkdocs_docs.py
	$(MKDOCS) build --strict
