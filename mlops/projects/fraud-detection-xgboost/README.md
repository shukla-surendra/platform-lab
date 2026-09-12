# fraud-detection-xgboost

An end-to-end MLOps pipeline for the fraud-detection use case: ingest a real
dataset, serve IP-reuse features from a Feast feature store, train an
XGBoost classifier, track it in MLflow, monitor it for drift with Evidently,
and serve it behind a FastAPI endpoint. Everything below was actually run,
not just written — see the numbers in "Results from a real run."

## Tools used

XGBoost, scikit-learn (`LogisticRegression`, `ColumnTransformer`/`Pipeline`
baseline), pandas/numpy, MLflow (tracking + registry, SQLite backend),
**Feast** (feature store — local provider, file registry, SQLite online
store), Evidently, FastAPI/Pydantic/Uvicorn, requests (Zenodo ingestion),
pytest, uv. Optional integration with the
[`k8s/k8s_mlops/practice/evidently_stack`](../../../k8s/k8s_mlops/README.md) Helm chart. Full
breakdown in [`FAQ.md`](FAQ.md)'s tools table.

## About the dataset

**[Zenodo record 20030065](https://zenodo.org/records/20030065)** — "A
Production-Collected Online Banking Fraud Detection Dataset from a Live
Cloud-Based Deep Learning System," CC-BY 4.0. 56,962 rows, 98 labeled fraud
(0.17%). Chosen over the other four datasets you listed because it's the
only one with both real fraud labels *and* a public, no-auth download URL —
Credit Card Fraud (ULB)/PaySim/IEEE-CIS are all Kaggle-hosted and need an
API token; UK Government Purchase Card has no fraud labels at all, so it
doesn't fit supervised classification.

**Two things worth knowing about it, found by inspecting the raw file
directly rather than trusting the abstract:**

1. **The row structure isn't uniform.** Some rows carry 28 dense,
   PCA-like `v1`–`v28` features that closely mirror the well-known ULB
   Credit Card Fraud dataset's `V1`–`V28` schema (same naming, same value
   ranges, even the same famous `amount=149.99` fraud example). Other rows
   have `v1`–`v28` mostly zero with a PaySim-style balance pattern instead
   (`v2`≈amount, `v3`/`v4` looking like before/after balances). That's
   unusual for one homogeneous production feed — worth being skeptical of
   the "live production system" framing rather than taking it at face
   value, though it doesn't block using the dataset for this exercise.
2. **`fraud_probability`, `risk_level`, `confidence`, and `recommendation`
   are the *source* system's own outputs**, not independent signal —
   `risk_level` is close to a direct restatement of `is_fraud`. Training on
   them would be leakage. `src/fraud_detection/config.py`'s
   `LEAKAGE_COLUMNS` drops all four; `tests/test_features.py` asserts they
   never reach the model.

## Data handling — nothing is stored in the repo

`src/fraud_detection/data.py` downloads the CSV straight from Zenodo into
`data/`, which is listed in `.gitignore` — the dataset is never committed,
by design. It's cached locally after the first download (rather than
re-fetched every run) purely for iteration speed; delete `data/` at any
time and the next run reproduces it from scratch. `mlflow.db`,
`evidently_report.html`, and `mlruns/` (all run-generated) are git-ignored
the same way.

## Pipeline stages

```
data.py                  -- download + cache the raw CSV (git-ignored)
features.py              -- leakage-free X/y split + chronological train/test split
feast_features.py        -- IP-reuse "velocity" features, served from Feast
train.py                 -- XGBoost + MLflow tracking + model registry (baseline)
train_with_feast.py      -- same, +Feast IP velocity features (separate registered model)
train_baseline_logreg.py -- ColumnTransformer + LogisticRegression, a third registered model
evaluate.py              -- score whatever's currently registered ("is what's deployed still good?")
monitor.py               -- Evidently drift report, reference=train period vs current=test period
serve.py                 -- FastAPI /predict (baseline) and /predict_feast (+Feast) endpoints
```

### Why a chronological split, not a random one

`features.temporal_train_test_split` splits by position after sorting on
`timestamp`, not `sklearn.train_test_split`'s random shuffle. Fraud data is
time-ordered; a random split would leak "future" transactions into training
and would hide real drift between the reference period and current
traffic — which matters here specifically because `monitor.py`'s whole job
is comparing "training-period" data against "current" data for drift, and
a random split would make that comparison meaningless.

### Why PR-AUC, not accuracy

At a 0.17% fraud rate, predicting "not fraud" for every single transaction
already scores 99.83% accuracy while catching zero fraud. `train.py` uses
`scale_pos_weight` (ratio of negative to positive class) so XGBoost doesn't
learn that shortcut, and reports **PR-AUC** (precision-recall AUC) as the
headline metric — the standard fix for evaluating classifiers on this level
of class imbalance, since ROC-AUC is more forgiving of imbalance than
PR-AUC is.

## Baseline comparison: logistic regression, and an honest correction

This README used to assert XGBoost was the right model choice based on
general reasoning (handles mixed scales, captures non-linear interactions,
`scale_pos_weight` for imbalance) without ever measuring it against a
simpler alternative. `train_baseline_logreg.py` closes that gap — and the
result reverses the original claim: a plain `LogisticRegression` scored
**PR-AUC 0.9252, ROC-AUC 0.9259** on the identical chronological split,
clearly beating XGBoost's 0.6758 / 0.8256.

This is the one place `sklearn.compose.ColumnTransformer` actually earns
its keep in this project. Verified directly: training XGBoost on raw
`amount` vs. `log1p(amount)` produced **byte-identical predictions** (tree
splits are invariant to monotonic per-feature transforms) — so scaling
would be theatre on the XGBoost path. Logistic regression has no such
invariance, and `amount` is badly skewed (skew ≈ 74, range $0.02–$659,035).
`build_pipeline()` uses `ColumnTransformer` to apply `log1p` + scaling to
`amount` specifically while scaling every other feature column plainly —
one `Pipeline`, logged whole to MLflow, so `serve.py`/`evaluate.py` would
never need to hand-reimplement this preprocessing (closing the
training/serving-skew gap that `serve.py`'s other two endpoints don't
currently have to worry about, but would the moment either needed
preprocessing of its own).

**This isn't the final word, on purpose.** Neither model's hyperparameters
were tuned, and the test period has only ~40 fraud examples — not enough
to retire XGBoost from consideration off one split. See `FAQ.md`'s Tier 3B
for the full reasoning and what a real resolution would require
(hyperparameter search + rolling-origin cross-validation for both models).
What this section is confident about is narrower and still valuable: the
original "why XGBoost" claim was unverified, and it's now been checked.

## Feature store: Feast

This dataset has no persistent customer/account ID at all — `ip_address` is
the only column that legitimately recurs across transactions (most of the
56,965 distinct IPs appear once; a few are reused dozens or hundreds of
times), which is exactly the shape Feast is built for: a recurring entity
whose features evolve over time. `feast_features.py` computes three
**leakage-safe, trailing** per-IP features — prior transaction count, prior
average amount, prior fraud count — using a `shift(1)`-before-aggregating
pattern so each row only ever sees transactions *strictly before* it from
the same IP. `feature_repo/` defines the `ip` entity and `ip_velocity_stats`
feature view; `train_with_feast.py` retrieves them for training via
`get_historical_features()` (Feast's point-in-time join), and
`serve.py`'s `/predict_feast` retrieves the *latest* materialized value via
`get_online_features()` for a live request.

**Honest result from a real run**: `train_with_feast.py` produced
**identical** PR-AUC/ROC-AUC to the baseline (0.6758 / 0.8256). Not a bug —
verified directly: the dominant IP-reuse burst (one IP reused 425 times) is
concentrated on 2026-04-10 to 2026-04-13, which falls entirely within the
last 30% of *rows* — but because event density is wildly non-uniform over
the 4-month timeline (dense in January, then sparse), that last-30%-by-row
-count window actually starts back on 2026-01-22, three months earlier than
the burst. Net effect: **every single nonzero occurrence of these features
landed in the test split, zero in training** — the model never saw a single
non-zero example of the feature during training, so it correctly learned to
ignore three constant-zero columns. This is a real, useful lesson, not a
disappointing result to hide: a feature store correctly serving a feature
with genuine real-world predictive value (IP reuse patterns are a
legitimate fraud signal) can still measure as useless if the train/test
split methodology doesn't happen to expose the model to it — see
`FAQ.md`'s Feast tier for the fuller discussion, including what a
calendar-time (not row-count) split would need to do differently.
`serve.py`'s `/predict_feast`, tested live against the heavily-reused IP,
correctly returns real, non-zero materialized values
(`ip_prior_txn_count: 424`, etc.) — the feature-serving mechanics work
correctly end to end; it's specifically the training-time exposure that's
the finding here.

## Results from a real run

```
uv run python -m fraud_detection.train
```

```
PR-AUC: 0.6758   ROC-AUC: 0.8256
```

```
uv run python -m fraud_detection.evaluate
```

On the held-out (chronologically later) test period: **96.4% precision,
67.5% recall** on fraud (27/40 caught, 1 false positive, 13 missed) —
consistent with a genuinely hard, low-signal fraud problem rather than a
toy one. A live prediction against one of the missed patterns (a
repeated, byte-identical `amount=149.99` fraud transaction that appears
several times in the raw file) came back as a false negative when tested
through `serve.py` — an honest example of the model's real limits, not
cherry-picked success.

## Setup (uv)

```bash
cd mlops_aiops/projects/fraud-detection-xgboost
uv sync
```

## Run it

```bash
NLTK_DISABLE_IMPORT_SECURITY=1 uv run python -m fraud_detection.train
NLTK_DISABLE_IMPORT_SECURITY=1 uv run python -m fraud_detection.train_with_feast
NLTK_DISABLE_IMPORT_SECURITY=1 uv run python -m fraud_detection.evaluate
NLTK_DISABLE_IMPORT_SECURITY=1 uv run python -m fraud_detection.monitor
```

`NLTK_DISABLE_IMPORT_SECURITY=1` is needed for the same reason documented in
[`docs/tools/evidently/README.md`](../../docs/tools/evidently/README.md) —
NLTK 3.10+'s import-security guard false-positives under uv/Jupyter, and
Evidently pulls in NLTK transitively even though this project uses no
text/LLM descriptors.

Browse the MLflow runs:

```bash
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Serve predictions:

```bash
NLTK_DISABLE_IMPORT_SECURITY=1 uv run uvicorn fraud_detection.serve:app --reload
curl -X POST localhost:8000/predict -H "Content-Type: application/json" -d '{"amount": 149.99, "time_value": 0, "v1": -1.36, "v2": -0.07, "v3": 2.54, "v4": 1.38, "v5": -0.34, "v6": 0.46, "v7": 0.24, "v8": 0.1, "v9": 0.36, "v10": 0.09, "v11": -0.55, "v12": -0.62, "v13": -0.99, "v14": -0.31, "v15": 1.47, "v16": -0.47, "v17": 0.21, "v18": 0.03, "v19": 0.4, "v20": 0.25, "v21": -0.02, "v22": 0.28, "v23": -0.11, "v24": 0.07, "v25": 0.13, "v26": -0.19, "v27": 0.13, "v28": -0.02}'
```

Or the Feast-augmented endpoint (needs `train_with_feast.py` to have run at
least once, which also materializes the online store):

```bash
curl -X POST localhost:8000/predict_feast -H "Content-Type: application/json" -d '{"amount": 149.99, "time_value": 0, "v1": -1.36, "v2": -0.07, "v3": 2.54, "v4": 1.38, "v5": -0.34, "v6": 0.46, "v7": 0.24, "v8": 0.1, "v9": 0.36, "v10": 0.09, "v11": -0.55, "v12": -0.62, "v13": -0.99, "v14": -0.31, "v15": 1.47, "v16": -0.47, "v17": 0.21, "v18": 0.03, "v19": 0.4, "v20": 0.25, "v21": -0.02, "v22": 0.28, "v23": -0.11, "v24": 0.07, "v25": 0.13, "v26": -0.19, "v27": 0.13, "v28": -0.02, "ip_address": "185.75.225.22"}'
```

Run tests (pure synthetic data — no download, no real dataset needed):

```bash
NLTK_DISABLE_IMPORT_SECURITY=1 uv run pytest
```

## Pushing drift reports to a real Evidently server

`monitor.py` checks `EVIDENTLY_SERVER_URL` and, if set, pushes the drift
report there via `RemoteWorkspace` instead of only saving it locally — this
plugs directly into
[`k8s/k8s_mlops/practice/evidently_stack`](../../../k8s/k8s_mlops/README.md), the Helm chart
that runs a self-hosted Evidently server in-cluster:

```bash
export EVIDENTLY_SERVER_URL=$(minikube service evidently-evidently-server -n evidently --url)
NLTK_DISABLE_IMPORT_SECURITY=1 uv run python -m fraud_detection.monitor
```

## Exploring the Feast store directly

`scripts/explore_feature_store.py` reads all three files Feast keeps in
`feature_repo/data/` — the offline Parquet source, the online SQLite store
(with its protobuf-encoded values decoded via Feast's own client, since raw
SQLite access can't do that), and the registry — and prints a summary of
each. Optionally pass `--ip` to also print one IP's decoded online-store
values:

```bash
NLTK_DISABLE_IMPORT_SECURITY=1 uv run python scripts/explore_feature_store.py --ip 185.75.225.22
```

## Related

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — component-by-component data flow,
  plus a [published diagram](https://claude.ai/code/artifact/a8961ad2-ccca-45c1-bd6c-5912f06fbca7)
  of the baseline vs. Feast-augmented lanes.
- [`FAQ.md`](FAQ.md) — interview-style Q&A over this project, easy to very
  hard, covering every design decision above in more depth (leakage
  mechanics, why chronological splits, MLflow registry gotchas, drift
  monitoring blind spots, production-readiness gaps, and systems-design
  curveballs).
- [`docs/tools/feast/README.md`](../../docs/tools/feast/README.md) — the
  full Feast write-up.
- [`projects/feast-demo/`](../feast-demo/) — the generic driver-stats
  version of the same entity/feature-view/feature-service loop.
- [`docs/tools/evidently/README.md`](../../docs/tools/evidently/README.md) —
  the full Evidently write-up.
- [`projects/evidently-monitoring-demo/`](../evidently-monitoring-demo/) —
  a smaller, synthetic-data version of the same drift-monitoring pattern.
- [`k8s/k8s_mlops/`](../../../k8s/k8s_mlops/) — the Kubernetes deployment of the
  Evidently server this project can optionally push reports to.
