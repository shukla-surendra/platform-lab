# batch-drift-detection-xgboost

A batch drift-detection **pipeline**, not a notebook: synthetic data ->
persisted XGBoost model -> predict on new batches -> generate new
synthetic batches with data drift, concept drift, or both -> Evidently
detects both. Every stage is a separate script writing a persisted
artifact the next stage loads — train once, then run `predict`/
`generate_drift`/`monitor` any number of times later, in separate
processes, the way a real batch system would.

Everything below was actually run against this project's own code — see
"Results from a real run."

**New to this project? Start with [`WALKTHROUGH.md`](WALKTHROUGH.md)
instead** — a step-by-step SOP with the exact commands in order, the real
output each one produces, and what to actually look at in that output and
why. This README is the reference doc (design decisions, the "why"); that
one is the "sit down and run it" doc.

## Why this exists alongside `evidently-monitoring-demo/`

[`../evidently-monitoring-demo/drift_types_with_evidently.ipynb`](../evidently-monitoring-demo/drift_types_with_evidently.ipynb)
already proved these exact drift-injection mechanics work, in one notebook,
cell by cell, with fresh synthetic data generated inline in each cell. This
project reuses the same proven mechanics (same `make_classification` shape,
same rescale-a-feature data-drift injection, same flip-labels-above-median
concept-drift injection) but turns them into a **reusable batch pipeline**
with real persisted artifacts: a saved model (`models/xgb_model.json`), a
saved scored reference set (`data/reference_scored.parquet`), and a CLI for
generating and scoring new batches independently, in later, separate runs
— matching a real deployment's actual shape (train once, score/monitor
repeatedly) rather than a single linear notebook walkthrough.

## Pipeline stages

```
synth_data.py       -- make_classification -> reference/holdout split (holdout persisted, reused by every later stage)
train.py             -- trains XGBoost on reference, saves models/xgb_model.json + data/reference_scored.parquet
predict.py            -- scores any batch with the persisted model ("use some data to predict")
generate_drift.py      -- draws a fresh batch from holdout, injects data drift / concept drift / both / neither
monitor.py               -- Evidently: DataDriftPreset + ClassificationPreset, reference vs. a current batch
```

## The two drift types, and how each is injected

| | Data drift (covariate shift) | Concept drift |
|---|---|---|
| Definition | Input feature distribution P(X) changes; the input→output relationship is untouched | The relationship P(Y\|X) itself changes — the same input now means something different |
| Injected by | `generate_drift.py --kind data`: rescale `feature_0` (`*1.8 + 3.0`), `target` copied through unchanged | `generate_drift.py --kind concept`: take a **fresh, unperturbed** sample (no feature touched) and flip the true label for the half of rows where `feature_1` is above its median |
| `DataDriftPreset` | Flags the perturbed column | Stays completely quiet — no feature was touched |
| `ClassificationPreset` | Accuracy barely moves | Accuracy collapses toward random guessing |

Full taxonomy (label drift, prediction drift, temporal drift patterns) and
why this particular pair is the one worth operationalizing first:
[`../../docs/tools/evidently/drift-detection-concepts.md`](../../docs/tools/evidently/drift-detection-concepts.md).

## Why `monitor.py` always runs both presets

Every batch `generate_drift.py` produces (`clean`/`data`/`concept`) keeps
its `target` column — the synthetic setup means "ground truth" is always
already known, unlike a real deployment where it typically lags behind
predictions by hours or days. `monitor.py` takes advantage of that to run
`DataDriftPreset` and `ClassificationPreset` together in one report and one
call, rather than modeling the real-world delay. In production, the
`DataDriftPreset` half would run the moment a batch exists (no ground
truth needed); the `ClassificationPreset` half would run later, once
outcomes arrive — see the drift-detection-concepts doc linked above for
that distinction in full.

## Setup (uv)

```bash
cd mlops_aiops/projects/batch-drift-detection-xgboost
uv sync
```

## Run it

```bash
export NLTK_DISABLE_IMPORT_SECURITY=1   # see "Environment quirks" below

uv run python -m batch_drift_detection.train
uv run python -m batch_drift_detection.predict                              # scores a fresh clean batch
uv run python -m batch_drift_detection.generate_drift --kind both           # writes current_clean/data/concept.parquet
uv run python -m batch_drift_detection.monitor --batch data/current_data.parquet
uv run python -m batch_drift_detection.monitor --batch data/current_concept.parquet
```

`generate_drift.py --kind data|concept|clean|both` can be re-run any time
after `train.py`, in a completely separate process — it only needs
`data/holdout.parquet` (written once by `train.py`) on disk, not anything
still in memory from training.

## Results from a real run

```
uv run python -m batch_drift_detection.train
```
```
Trained on 4800 reference rows, 8 features.
Holdout sanity check -- accuracy: 0.971, ROC-AUC: 0.992
```

```
uv run python -m batch_drift_detection.monitor --batch data/current_data.parquet
```
```
Data drift detected:      False
Drifted columns:          1 (10%)
Accuracy  reference -> current:  1.000 -> 0.941
```

```
uv run python -m batch_drift_detection.monitor --batch data/current_concept.parquet
```
```
Data drift detected:      False
Drifted columns:          0 (0%)
Accuracy  reference -> current:  1.000 -> 0.487
```

This is the whole point of the project, reproduced with real numbers: the
data-drift batch gets caught directly (1 column flagged) with accuracy
barely moving; the concept-drift batch sails through `DataDriftPreset`
completely clean (**0 columns flagged — "dataset drift: False"**) while
accuracy collapses to **essentially a coin flip**. A monitoring setup that
only watches feature drift would report a clean bill of health here while
the model is actively failing on half the incoming population.

**One caveat worth being explicit about**: "reference accuracy: 1.000" is
the model scored on its own *training* data (`reference_scored.parquet`
*is* the training set XGBoost fit on) — it's inflated by definition, not a
genuine held-out number. The `train.py` sanity-check accuracy (0.971, on
the never-trained-on holdout pool) is the honest baseline; treat the
`reference -> current` deltas above as directional signal, not the
absolute 1.000 as a real accuracy ceiling.

`Data drift detected: False` in both cases refers to the **dataset-level**
`dataset_drift` flag, which only flips once the *share* of drifted columns
crosses a default 50% threshold — the same nuance
`drift_types_with_evidently.ipynb` calls out. `Drifted columns: 1 (10%)`
on the data-drift run is the signal that actually matters here; the
dataset-level boolean staying `False` is expected, not a miss.

## Environment quirks

Same two issues already documented and solved in
[`../evidently-monitoring-demo/README.md`](../evidently-monitoring-demo/README.md#known-environment-quirks-already-handled-documented-for-context):

- **`NLTK_DISABLE_IMPORT_SECURITY=1` is required** — NLTK 3.10+'s
  import-security guard false-positives on Evidently's transitive NLTK
  import whenever the working directory is on `sys.path` (which `uv run`
  adds by default).
- **`ClassificationPreset`/`ColumnMapping` live under `evidently.legacy.*`**
  in current Evidently (0.7.x) — `monitor.py` imports from there
  deliberately, not from the newer top-level `evidently.Report`/`presets`
  API, since the legacy combination is what's actually been run and
  verified in this repo (also true of `fraud-detection-xgboost/monitor.py`,
  which uses the newer API but only for `DataDriftPreset` — it never needed
  `ClassificationPreset`).

## Tests

Pure synthetic data, no network — actually run, 7 passed:

```bash
uv run pytest
```

`test_monitor.py` is the interesting one: it reruns this project's own
`inject_data_drift`/`inject_concept_drift` + `run_monitor` and asserts the
same pattern shown above (data drift flags >=1 column without collapsing
accuracy; concept drift flags 0 columns while accuracy drops by more than
0.2) — a regression test for the exact phenomenon this project exists to
demonstrate, not just "does it run without crashing."

## Related

- [`../evidently-monitoring-demo/`](../evidently-monitoring-demo/) — the
  notebook this project's drift-injection mechanics are drawn from, plus
  the batch+MLflow monitoring pattern `monitor.py` follows.
- [`../../docs/tools/evidently/drift-detection-concepts.md`](../../docs/tools/evidently/drift-detection-concepts.md) —
  the full drift taxonomy (including label drift and prediction drift,
  not covered by this project) and why covariate-only monitoring misses
  concept drift structurally, not as an edge case.
- [`../../docs/tools/evidently/README.md`](../../docs/tools/evidently/README.md) —
  full Evidently write-up.
- [`../fraud-detection-xgboost/`](../fraud-detection-xgboost/) — the same
  stage-script pipeline shape (`train.py`/`evaluate.py`/`monitor.py`)
  applied to a real downloaded dataset instead of synthetic data.
