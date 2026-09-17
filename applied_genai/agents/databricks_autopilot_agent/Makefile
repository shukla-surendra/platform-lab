PYTHON ?= python3

.PHONY: install pull reset watch fix simulate simulate-forever tail-audit clean

install:
	$(PYTHON) -m pip install -r requirements.txt

pull:
	ollama pull qwen3.5:latest

reset:
	$(PYTHON) reset_state.py

watch:
	$(PYTHON) daemon.py

fix:
	$(PYTHON) daemon.py --apply

simulate:
	$(PYTHON) event_simulator.py --scenario $(or $(SCENARIO),mixed)

simulate-forever:
	$(PYTHON) event_simulator.py --forever

tail-audit:
	tail -f audit_log.jsonl

clean:
	rm -f pipeline_state.json audit_log.jsonl
	rm -f events/inbox/*.json events/processed/*.json events/failed/*.json
