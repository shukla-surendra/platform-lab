PYTHON ?= python3

PIPE_DIR := .pipes
REQUEST_PIPE := $(PIPE_DIR)/request.pipe
RESPONSE_PIPE := $(PIPE_DIR)/response.pipe
PID_FILE := .server.pid
LOG_FILE := server.log

.PHONY: jsonrpc-demo client-smoke-test demo demo-quiet compare \
	server-bg server-stop server-status notebook-install notebook clean

jsonrpc-demo:
	$(PYTHON) jsonrpc.py

client-smoke-test:
	$(PYTHON) mcp_client.py

demo:
	$(PYTHON) demo.py

demo-quiet:
	$(PYTHON) demo.py --quiet

compare:
	diff -u ../bedrock_agentcore_demo/tasks_mcp_server.py mcp_server.py || true

# --- background server, for the Jupyter notebook demo --------------------------------------------
#
# Runs mcp_server.py detached from this terminal, talking over a pair of named pipes instead of
# stdin/stdout (see mcp_server.py's --pipe-in/--pipe-out). Unlike mcp_client.py's MCPClient(...),
# which spawns and owns a server subprocess for its own lifetime, this lets an independent process
# (a Jupyter kernel, or a second terminal) attach later via MCPClient.connect(...) and keep using
# the same server -- and the same tasks.json state -- across many cells or reconnects.

server-bg:
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "server already running (pid $$(cat $(PID_FILE))) -- run 'make server-stop' first"; \
		exit 1; \
	fi
	@mkdir -p $(PIPE_DIR)
	@rm -f $(REQUEST_PIPE) $(RESPONSE_PIPE)
	@mkfifo $(REQUEST_PIPE) $(RESPONSE_PIPE)
	@( $(PYTHON) mcp_server.py --pipe-in $(REQUEST_PIPE) --pipe-out $(RESPONSE_PIPE) \
		> $(LOG_FILE) 2>&1 & echo $$! > $(PID_FILE) )
	@echo "server started in background (pid $$(cat $(PID_FILE)))"
	@echo "  request pipe:  $(REQUEST_PIPE)"
	@echo "  response pipe: $(RESPONSE_PIPE)"
	@echo "  logs:          tail -f $(LOG_FILE)"
	@echo "connect from Python/Jupyter with:"
	@echo "  MCPClient.connect('$(REQUEST_PIPE)', '$(RESPONSE_PIPE)')"
	@echo "see mcp_from_scratch_notebook.ipynb for a full walkthrough"

server-status:
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "running (pid $$(cat $(PID_FILE)))"; \
	else \
		echo "not running"; \
	fi

server-stop:
	@if [ -f $(PID_FILE) ]; then \
		kill $$(cat $(PID_FILE)) 2>/dev/null || true; \
		rm -f $(PID_FILE); \
		echo "server stopped"; \
	else \
		echo "no $(PID_FILE) found -- is a server running? (make server-bg)"; \
	fi
	@rm -f $(REQUEST_PIPE) $(RESPONSE_PIPE)

notebook-install:
	$(PYTHON) -m pip install -q -r requirements-notebook.txt

notebook: notebook-install
	$(PYTHON) -m jupyter notebook mcp_from_scratch_notebook.ipynb

clean:
	rm -f tasks.json $(PID_FILE) $(LOG_FILE)
	rm -rf $(PIPE_DIR) .ipynb_checkpoints
