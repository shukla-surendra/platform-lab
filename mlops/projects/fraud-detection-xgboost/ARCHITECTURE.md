# Architecture

How the pieces in this project actually connect — component by component,
following the real flow of data through `data.py → features.py →
{train.py, train_with_feast.py} → MLflow → {evaluate.py, serve.py}`, with
`monitor.py` and Feast's offline/online split drawn out explicitly. See
[`README.md`](README.md) for *why* each decision was made and
[`FAQ.md`](FAQ.md) for the interview-depth version of each; this doc is
about *what talks to what*.

## Diagram

```
                                                     ┌─────────────┐
                                                ┌────▶│ evaluate.py │
                                                │     └─────────────┘
                                                │      loads models:/<name>/latest
 ┌────────┐   ┌─────────┐   ┌───────────────┐   │
 │ Zenodo │──▶│ data.py │──▶│  features.py  │───┤ raw train_df/test_df
 │ (CSV)  │   │ (cache) │   │ (chrono split)│   │
 └────────┘   └─────────┘   └───────┬───────┘   │
                                     │           │      ┌──────────────────┐   ┌───────────────┐
                                     │           ├──────▶│    train.py      │──▶│ MLflow         │──▶│ serve.py       │
                                     │  raw only │       │   (baseline)     │   │ tracking +     │   │  /predict      │
                                     │           │       └──────────────────┘   │ registry:      │   └───────────────┘
                                     │           │                              │  fraud-xgboost │
                                     │           │       ┌──────────────────┐   │  fraud-xgboost-│   ┌───────────────┐
                                     │           └──────▶│ get_historical_  │──▶│  feast         │──▶│ serve.py       │
                                     │                    │ features()       │   └───────┬────────┘   │ /predict_feast │
                                     │                    │ (point-in-time   │           │            └──────┬────────┘
                                     │                    │  join)           │           │                   │
                                     │                    └────────▲─────────┘           │                   │
                                     │                             │                      │                   │
                                     │  full history        ┌──────┴───────┐              │                   │
                                     └──────────────────────▶│ ip_velocity_ │              │      get_online_features()
                                        (built once,          │ stats.parquet│              │        (latest value)
                                         shift(1)-safe)        │ (offline)    │              │                   │
                                                               └──────────────┘              │                   │
                                                                       │                      ▼                   │
                                                            materialize_incremental() ┌──────────────┐            │
                                                                       └─────────────▶│ online store │◀───────────┘
                                                                                       │  (SQLite)    │
                                                                                       └──────────────┘

 ┌───────────────┐   train_df/test_df, raw features   ┌────────────────┐   ┌──────────────────────┐
 │ features.py   │────────────────────────────────────▶│  monitor.py    │──▶│ Evidently Report      │
 └───────────────┘                                     │ (drift check)  │   │ (evidently_report.html)│
                                                        └────────────────┘   └──────────┬────────────┘
                                                                                          │ if EVIDENTLY_SERVER_URL set
                                                                                          ▼
                                                                              ┌───────────────────────┐
                                                                              │ remote Evidently server │
                                                                              │  (optional, out of scope│
                                                                              │  of this doc — see      │
                                                                              │  k8n_mlops/README.md)   │
                                                                              └───────────────────────┘
```

A cleaner, colored version of the same diagram (baseline lane vs. the
Feast-augmented lane drawn as two visually distinct paths) is published
[here](https://claude.ai/code/artifact/a8961ad2-ccca-45c1-bd6c-5912f06fbca7),
and also saved locally as
[`architecture-diagram.html`](architecture-diagram.html) — a standalone
file, open it directly in a browser, no server needed.

## Components

| Component | Role | Talks to |
|---|---|---|
| `data.py` | Downloads the raw CSV from Zenodo once, caches it (git-ignored) | Zenodo's public file URL |
| `features.py` | Leakage-free `X`/`y` split; chronological (not random) train/test split | Nothing external — pure pandas |
| `feast_features.py` | Builds the leakage-safe IP-velocity source; wraps Feast's `apply`/`get_historical_features`/`materialize_incremental`/`get_online_features` | `feature_repo/` (Feast's file registry, Parquet offline store, SQLite online store) |
| `train.py` | Trains the baseline XGBoost model on raw features only | `data.py`, `features.py`, MLflow |
| `train_with_feast.py` | Same training loop, plus the Feast-served IP-velocity features | `data.py`, `features.py`, `feast_features.py`, MLflow |
| MLflow (`mlflow.db`) | Tracking (params/metrics/artifacts per run) + model registry (two named models: `fraud-xgboost`, `fraud-xgboost-feast`) | Written to by both `train*.py`; read by `evaluate.py` and `serve.py` |
| `evaluate.py` | Reloads whatever's currently registered and scores it against a fresh test split — independent of what `train.py` just produced | MLflow registry |
| `serve.py` | FastAPI app: `/predict` (baseline model) and `/predict_feast` (Feast model + a live online-store lookup by `ip_address`) | MLflow registry, Feast online store |
| `monitor.py` | Evidently drift report comparing the training period's raw features against the test period's | `features.py`'s split output; optionally a remote Evidently server via `RemoteWorkspace` |

## The one fork that matters: baseline vs. Feast-augmented

Two training scripts, two registered models, two serving endpoints — not
one pipeline with a feature-store toggle. `train.py`'s numbers were
measured and documented first; `train_with_feast.py` exists to produce an
honest, independently-reproducible A/B comparison against them rather than
silently changing what `train.py` already reported. See `README.md`'s
"Feature store: Feast" section for the actual result of that comparison
(identical PR-AUC — a real, diagnosed finding, not a bug) and `FAQ.md`'s
Tier 2B for the full mechanism behind why.

## Feast: two stores, two access patterns

The mechanism worth understanding precisely, not just the name "feature
store": `ip_velocity_stats.parquet` (the **offline** store) is built once
from the *entire* chronological history. `train_with_feast.py` queries it
through `get_historical_features()` — a **point-in-time join**: for each
transaction's own `(ip_address, timestamp)`, Feast returns that IP's
velocity stats as they stood at that exact moment, never a later value.
Separately, `materialize_incremental()` copies each IP's *latest* values
into the **online** store (SQLite) — a plain key-value table. `serve.py`'s
`/predict_feast` queries that online store through `get_online_features()`,
a point lookup with no timestamp involved, the way a live request actually
works. Same feature definitions, two different retrieval mechanisms — that
split is the entire reason Feast exists, not an incidental implementation
detail.

## Related

- [`README.md`](README.md) — why each of these decisions was made, and the
  real numbers from real runs.
- [`FAQ.md`](FAQ.md) — interview-depth Q&A on every component above.
- [`docs/tools/feast/README.md`](../../docs/tools/feast/README.md) and
  [`docs/tools/mlflow/README.md`](../../docs/tools/mlflow/README.md) — the
  general tool write-ups these components are specific applications of.
