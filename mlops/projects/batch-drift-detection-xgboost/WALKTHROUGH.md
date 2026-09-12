# Walkthrough / SOP — batch-drift-detection-xgboost

A step-by-step runbook: exact commands, in order, with the **real output**
each one produces (captured from an actual run of this project — nothing
here is simulated), plus what to actually look at in that output and why.
[`README.md`](README.md) is the reference doc (design decisions, "why this
instead of that"); this file is the "sit down and run it" doc.

If you haven't touched this project before, run every command below in
order once, top to bottom, before branching off into your own experiments.

## What you're about to build

Four things happen, each a separate command, each writing a file the next
command reads — this is a real pipeline, not a notebook you run top to
bottom in one sitting:

```
1. TRAIN     synthetic data -> XGBoost model -> saved to disk
2. PREDICT   saved model -> score a fresh batch of "production" data
3. DRIFT     generate a NEW synthetic batch, deliberately broken two
             different ways (data drift, concept drift)
4. MONITOR   Evidently compares the broken batch to the original
             reference data and tells you what it can and can't see
```

The whole point of step 4 is a specific, slightly uncomfortable lesson:
**one of the two ways of breaking the data is completely invisible to
feature-distribution monitoring.** You'll see that directly, in your own
terminal output, in step 3C below — not just told about it.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) installed (`uv --version` should work)
- Nothing else — no AWS/GCP account, no GPU, no external service. Everything
  runs locally against synthetic data.

## Step 0 — Install dependencies

```bash
cd mlops_aiops/projects/batch-drift-detection-xgboost
uv sync
```

This creates `.venv/` and installs pandas, scikit-learn, xgboost, evidently,
and mlflow at the exact versions pinned in `uv.lock`. Takes under a minute.

Set this once per terminal session, before running anything below:

```bash
export NLTK_DISABLE_IMPORT_SECURITY=1
```

**Why:** Evidently pulls in NLTK transitively (for text-drift features this
project never uses). NLTK 3.10+ has a security guard that false-positives
whenever the current directory is on `sys.path` — which `uv run` does by
default. The env var is NLTK's own documented escape hatch. Skip this and
`import evidently` will fail with a confusing NLTK import error, not
anything about your code.

## Step 1 — Generate data and train the model

```bash
uv run python -m batch_drift_detection.train
```

**What actually happens, under the hood:**
1. `synth_data.py` calls `sklearn.datasets.make_classification` to build
   8,000 rows, 8 features, 2 classes — a synthetic dataset with a real,
   learnable pattern (not random noise).
2. That's split 60/40 into a **reference** set (what the model trains on)
   and a **holdout** pool (never seen during training — this is what steps
   2 and 3 draw "new" batches from later, simulating fresh production data).
3. `train.py` fits an `XGBClassifier` on the reference set.
4. The model is saved to `models/xgb_model.json`, and the reference set
   (with the model's own predictions attached) is saved to
   `data/reference_scored.parquet` — this becomes Evidently's comparison
   baseline in every later step.

**Real output:**
```
Trained on 4800 reference rows, 8 features.
Holdout sanity check -- accuracy: 0.971, ROC-AUC: 0.992
Model saved to .../models/xgb_model.json
Scored reference saved to .../data/reference_scored.parquet
```

**What to check:** `0.971` accuracy on the holdout pool (data the model
never trained on) — this confirms the model actually learned something
real, not just memorized the training set. If this were suspiciously low
(near 0.5, a coin flip) or suspiciously perfect (1.000), something would be
wrong before you even get to drift detection.

**Run this once.** Everything after this step just loads the files it
wrote — you don't need to retrain to run steps 2–4 again later, even in a
brand new terminal session.

## Step 2 — Run inference on new data

```bash
uv run python -m batch_drift_detection.predict
```

**What happens:** loads `models/xgb_model.json`, samples 800 fresh rows
from `data/holdout.parquet` (data the model has genuinely never seen —
this is standing in for "today's production traffic"), scores them, and
saves the result to `data/scored_clean_batch.parquet`.

**Real output:**
```
Scored 800 rows -> .../data/scored_clean_batch.parquet
Predicted class balance:
prediction
0    0.50875
1    0.49125
```

**What to check:** the predicted class balance (roughly 50/50 here) —
this is the model behaving normally on ordinary data, your baseline for
"what does healthy look like" before you intentionally break something in
the next step.

You can also score any file of your own instead of a fresh sample:
```bash
uv run python -m batch_drift_detection.predict --batch path/to/your.parquet --out data/scored_custom.parquet
```

## Step 3 — Generate drifted data (both kinds, side by side)

```bash
uv run python -m batch_drift_detection.generate_drift --kind both
```

**Real output:**
```
[clean]   800 rows -> .../data/current_clean.parquet
[data]    800 rows -> .../data/current_data.parquet
[concept] 800 rows -> .../data/current_concept.parquet
```

Three files, three different batches, all sampled from the same holdout
pool — the *only* thing that differs between them is what got broken:

- **`current_clean.parquet`** — untouched. A control group: what does
  Evidently say when nothing is actually wrong?
- **`current_data.parquet`** — **data drift** injected: `feature_0` is
  rescaled (`x * 1.8 + 3.0`). The true label (`target`) is copied through
  unchanged. Think: an upstream sensor got recalibrated, or a unit changed
  from cents to dollars — the *meaning* of the data hasn't changed, its
  *scale* has.
- **`current_concept.parquet`** — **concept drift** injected: no feature is
  touched at all. Instead, the true label is *flipped* for every row where
  `feature_1` is above its own median. Think: the real-world rule
  connecting inputs to outcomes changed — the same input now means
  something different than it used to.

You can generate just one kind, with your own parameters, instead of all
three:
```bash
uv run python -m batch_drift_detection.generate_drift --kind data --feature feature_2 --scale 2.5 --shift -1.0
uv run python -m batch_drift_detection.generate_drift --kind concept --slice-feature feature_3
```

## Step 4 — Detect drift with Evidently

Run all three and compare — this is where the lesson lands.

### 4A. The control (nothing should fire)

```bash
uv run python -m batch_drift_detection.monitor --batch data/current_clean.parquet
```
```
Data drift detected:      False
Drifted columns:          0 (0%)
Accuracy  reference -> current:  1.000 -> 0.973
```
Quiet, as expected — this batch wasn't touched.

### 4B. Data drift (should be caught directly)

```bash
uv run python -m batch_drift_detection.monitor --batch data/current_data.parquet
```
```
Data drift detected:      False
Drifted columns:          1 (10%)
Accuracy  reference -> current:  1.000 -> 0.941
```
**Read this carefully — `Data drift detected: False` here is not a bug.**
That's the *dataset-level* flag, which only flips `True` once more than
50% of columns are individually flagged. Only 1 of 10 tracked columns
(`feature_0`, the one we rescaled) is drifted — that's the number that
matters, and it's correctly nonzero. Accuracy barely moved (1.000 → 0.941)
because the model still generalizes fine to a rescaled-but-not-relabeled
input.

### 4C. Concept drift — the important one

```bash
uv run python -m batch_drift_detection.monitor --batch data/current_concept.parquet
```
```
Data drift detected:      False
Drifted columns:          0 (0%)
Accuracy  reference -> current:  1.000 -> 0.487
```
**This is the whole point of the project.** Zero drifted columns — feature
monitoring found *nothing wrong* — while accuracy collapsed from perfect to
essentially a coin flip. A monitoring setup watching only `DataDriftPreset`
would report a clean bill of health here while the model is actively
failing on half the population it's scoring. Only the accuracy column
(which needed the true labels — something a real production system usually
doesn't have until later) caught it.

Put 4B and 4C side by side and the asymmetry is the takeaway: **data drift
shows up in the features and barely touches accuracy; concept drift is
invisible in the features and devastates accuracy.** Neither check alone
is sufficient — that's why `monitor.py` always runs both.

## Understanding what got saved

```
data/
  holdout.parquet            -- the pool step 2/3 draw "new" batches from
  reference_scored.parquet   -- what every monitor.py run compares against
  scored_clean_batch.parquet -- output of step 2
  current_clean.parquet      -- output of step 3 (control)
  current_data.parquet       -- output of step 3 (data drift)
  current_concept.parquet    -- output of step 3 (concept drift)
models/
  xgb_model.json             -- the trained model, reloaded by predict.py and monitor.py
reports/
  current_clean.html         -- full interactive Evidently report per batch
  current_data.html
  current_concept.html
mlflow.db                    -- every train/monitor run's metrics, queryable
```

**Open a report directly** (no server needed — it's a static HTML file):
```bash
open reports/current_concept.html   # macOS
xdg-open reports/current_concept.html   # Linux
```
This is worth doing at least once — the printed summary above is a small
slice of what's in there (full confusion matrix, per-feature drift
breakdown, distribution plots for every column).

**Browse every run's history in MLflow:**
```bash
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```
Then open http://127.0.0.1:5000 — each `train`/`monitor` invocation is its
own run, with metrics and the HTML report attached as an artifact.

## Re-running from scratch

Everything under `data/`, `models/`, `reports/`, and `mlflow.db` is
regenerated by the commands above (all git-ignored) — safe to delete any or
all of it and start over:

```bash
rm -rf data/ models/ reports/ mlflow.db mlruns/
uv run python -m batch_drift_detection.train
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError` mentioning NLTK on `import evidently` | `NLTK_DISABLE_IMPORT_SECURITY` not set | `export NLTK_DISABLE_IMPORT_SECURITY=1` before running anything |
| `FileNotFoundError: No trained model at .../xgb_model.json` | Ran `predict`/`monitor` before `train` | Run Step 1 first — everything else depends on its output |
| `FileNotFoundError: No holdout pool at .../holdout.parquet` | Same as above | Same fix — `train.py` (via `synth_data.py`) is what creates the holdout pool |
| Numbers differ slightly from this doc | Different `--seed`/`--n` than the defaults used here | Expected — the *pattern* (data drift caught, concept drift invisible-but-devastating) should hold regardless of the exact numbers; if the pattern itself disappears, something's actually wrong |

## Run the test suite

Confirms the pattern above holds as a regression test, not just this one
manual run — pure synthetic data, no network, ~1 minute:

```bash
uv run pytest
```

## Where to go next

- [`README.md`](README.md) — why each design decision was made (why
  `evidently.legacy.*`, why a persisted-artifact pipeline instead of a
  notebook, why the reference-accuracy caveat matters).
- [`../../docs/tools/evidently/drift-detection-concepts.md`](../../docs/tools/evidently/drift-detection-concepts.md) —
  the full drift taxonomy (this project covers 2 of ~6 types — label
  drift, prediction drift, and the sudden/gradual/incremental/recurring
  temporal patterns aren't covered here).
- [`../evidently-monitoring-demo/drift_types_with_evidently.ipynb`](../evidently-monitoring-demo/drift_types_with_evidently.ipynb) —
  every drift type from that taxonomy, isolated in its own notebook cell.
- [`/home/surendra/projects/platform-lab/manual_notes/Model & Data Drift.md`](../../../manual_notes/Model%20&%20Data%20Drift.md) —
  the conceptual reference doc this project's real numbers are cited in.
