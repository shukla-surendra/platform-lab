PYTHON ?= python3

.PHONY: install pull seed seed-incident investigate fix chat clean

install:
	$(PYTHON) -m pip install -r requirements.txt

pull:
	ollama pull qwen3.5:latest

seed:
	$(PYTHON) seed_incident.py

seed-incident:
	$(PYTHON) seed_incident.py --incident

investigate:
	$(PYTHON) sre_agent.py --trace "$(Q)"

fix:
	$(PYTHON) sre_agent.py --apply --trace "$(Q)"

chat:
	$(PYTHON) sre_agent.py --session $(or $(SESSION),default) --trace "$(Q)"

clean:
	rm -f infra_state.json sre_sessions.sqlite
