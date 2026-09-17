PYTHON ?= python3

.PHONY: install benchmark install-notebook lab lab-databricks clean

install:
	$(PYTHON) -m pip install -r requirements.txt

benchmark:
	$(PYTHON) benchmark.py

install-notebook:
	$(PYTHON) -m pip install -r requirements-notebook.txt
	$(PYTHON) -m ipykernel install --user --name=similarity-search --display-name "Similarity Search (local)"

lab:
	jupyter lab --port=8891 explore.ipynb

lab-databricks:
	jupyter lab --port=8891 databricks_vector_search.ipynb

clean:
	rm -rf __pycache__ .ipynb_checkpoints
