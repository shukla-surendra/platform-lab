PYTHON ?= .venv/bin/python

.PHONY: install pull seed investigate fix chat clean

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.txt

pull:
	ollama pull llama3.1:8b

seed:
	$(PYTHON) seed_incident.py

investigate:
	$(PYTHON) agent.py "$(Q)"

fix:
	$(PYTHON) agent.py "$(Q). If you find the cause, restart the affected deployment."

chat:
	$(PYTHON) agent.py --thread $(or $(THREAD),default)

clean:
	kubectl delete namespace $$( .venv/bin/python -c "import config; print(config.DEMO_NAMESPACE)" ) --ignore-not-found
	rm -f agent_memory.sqlite
