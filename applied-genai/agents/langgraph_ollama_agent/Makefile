PYTHON ?= python3

.PHONY: install pull ask chat stream clean

install:
	$(PYTHON) -m pip install -r requirements.txt

pull:
	ollama pull qwen3.5:latest

ask:
	$(PYTHON) agent.py "$(Q)"

chat:
	$(PYTHON) agent.py --thread $(or $(THREAD),default)

stream:
	$(PYTHON) agent.py --stream "$(Q)"

clean:
	rm -f agent_memory.sqlite notes.json
