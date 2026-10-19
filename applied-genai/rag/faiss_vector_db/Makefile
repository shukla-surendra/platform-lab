PYTHON ?= python3

.PHONY: install demo ingest search ask clean

install:
	$(PYTHON) -m pip install -r requirements.txt

demo:
	$(PYTHON) lifecycle_demo.py

ingest:
	$(PYTHON) ingest.py

search:
	$(PYTHON) search.py "$(Q)"

ask:
	$(PYTHON) rag.py "$(Q)"

clean:
	rm -rf data
