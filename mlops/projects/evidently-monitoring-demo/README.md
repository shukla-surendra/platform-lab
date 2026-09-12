# Evidently monitoring demo

Two runnable Jupyter notebooks, both executed end-to-end against the
uv-managed environment in this folder (see "Known environment quirks"
below for the real issues that came up and how they're handled):

- **[`evidently_xgboost_monitoring.ipynb`](evidently_xgboost_monitoring.ipynb)**
  — drift + classification-performance monitoring with Evidently and
  XGBoost, logged to MLflow. Standalone version of the pattern documented
  in [`docs/tools/evidently/README.md`](../../docs/tools/evidently/README.md)
  (the 4-hour Databricks batch example) — uses synthetic data and local
  pandas/MLflow instead of Delta tables and Databricks Workflows, so it
  runs anywhere without a cluster.
- **[`drift_types_with_evidently.ipynb`](drift_types_with_evidently.ipynb)**
  — companion notebook to
  [`docs/tools/evidently/drift-detection-concepts.md`](../../docs/tools/evidently/drift-detection-concepts.md).
  Walks through every widely accepted drift type (data/covariate, label,
  concept, prediction, plus sudden/gradual/incremental/recurring temporal
  patterns) as a small, isolated, runnable example each, showing exactly
  which Evidently metric/preset catches which — including the one case
  (concept drift) that feature-only drift monitoring cannot see at all.

## Setup (uv)

Managed with [uv](https://docs.astral.sh/uv/) — dependencies are declared
in `pyproject.toml`, pinned in `uv.lock`.

```bash
cd projects/evidently-monitoring-demo
uv sync
```

This creates `.venv/` and installs everything (pandas, scikit-learn,
xgboost, evidently, mlflow, jupyter) at the versions in `uv.lock`. No
separate `pip install` step needed.

## Run it

Interactively, in Jupyter (either notebook):

```bash
NLTK_DISABLE_IMPORT_SECURITY=1 uv run jupyter notebook evidently_xgboost_monitoring.ipynb
NLTK_DISABLE_IMPORT_SECURITY=1 uv run jupyter notebook drift_types_with_evidently.ipynb
```

Headlessly, to just execute one end-to-end and bake in the outputs (useful
for CI-style "does it still run" checks):

```bash
NLTK_DISABLE_IMPORT_SECURITY=1 uv run jupyter nbconvert --to notebook --execute --inplace evidently_xgboost_monitoring.ipynb
NLTK_DISABLE_IMPORT_SECURITY=1 uv run jupyter nbconvert --to notebook --execute --inplace drift_types_with_evidently.ipynb
```

`evidently_xgboost_monitoring.ipynb` also logs to MLflow — browse the run
(the Evidently HTML report + drift metric) with:

```bash
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```

`drift_types_with_evidently.ipynb` doesn't use MLflow at all — it's pure
Evidently, focused on the drift taxonomy rather than the logging pipeline.

## Known environment quirks (already handled, documented for context)

- **`NLTK_DISABLE_IMPORT_SECURITY=1` is required.** NLTK 3.10+ ships a
  legitimate security hardening feature (`nltk/inisec.py`, CWE-427
  mitigation) that blocks NLTK's own internal imports whenever the current
  working directory is on `sys.path` — which Jupyter/uv add by default.
  Evidently pulls in NLTK transitively (for text/LLM descriptors we don't
  even use here), so this false-positive fires on plain `import evidently`.
  The env var above is NLTK's own documented escape hatch for this exact
  situation — nothing malicious involved, verified by reading
  `nltk/inisec.py` directly.
- **Evidently's classic API moved under `evidently.legacy`.** Current
  Evidently (0.7.x) ships a new core API; the familiar
  `Report`/`ColumnMapping`/`metric_preset` interface used in this notebook
  and most existing tutorials still exists, just under
  `evidently.legacy.*` (e.g. `from evidently.legacy.report import Report`).
- **MLflow's plain filesystem store (`./mlruns`) is in maintenance mode.**
  Current MLflow refuses to use it by default and recommends a database
  backend even for local use — this notebook uses
  `sqlite:///mlflow.db` instead.

## Related docs

- [`../batch-drift-detection-xgboost/`](../batch-drift-detection-xgboost/) —
  the data-drift/concept-drift pair from `drift_types_with_evidently.ipynb`
  turned into a reusable batch pipeline (persisted model, separate train/
  predict/generate-drift/monitor stages) instead of a one-off notebook run.
- [Evidently](../../docs/tools/evidently/README.md) — full write-up,
  alternatives, server requirements, MLflow relationship.
- [MLflow](../../docs/tools/mlflow/README.md) — tracking backbone used here.
- [Databricks example](../../docs/tools/evidently/examples/databricks_xgboost_batch_monitoring.py) —
  the production version this notebook is a standalone stand-in for.
