# 03-drift-engine

The core of [`../`](../): two ways of asking the same question — "does the
`amount` feature in the current event stream look like the reference
distribution?" — using [Evidently](../../../mlops_aiops/docs/tools/evidently/README.md).
This is where the batch/streaming experimentation the project was scoped
around actually lives.

**Status: scaffolded, not installed / not run.** [`batch/run_batch_drift_check.py`](batch/run_batch_drift_check.py)
and [`streaming/run_streaming_drift_check.py`](streaming/run_streaming_drift_check.py)
use the real `evidently==0.7.21` API (`Dataset.from_pandas` /
`DataDefinition` / `Report` / `ValueDrift`, confirmed against
[`../../k8s/k8s_mlops/evidently_stack/notebooks/evidently_client_demo.ipynb`](../../k8s/k8s_mlops/evidently_stack/notebooks/evidently_client_demo.ipynb),
the one place in this repo Evidently has actually been run), but neither
script has been executed yet — `extract_drift_score()` in particular guesses
at `snapshot.dict()`'s shape and is flagged inline as unverified. Run it
against a real Evidently install first and fix that function if the shape's
different.

## Batch vs. streaming: the actual design

Both are entrypoints of **one** chart, sharing
[`common/otel_metrics.py`](common/otel_metrics.py) (the OTLP emitter) and
[`common/reference_data.py`](common/reference_data.py) (the fixed reference
distribution, calibrated to match
[`../01-ingestion/values.yaml`](../01-ingestion/values.yaml)'s
`producer.driftBaselineMean`) — so a drift score computed by one is directly
comparable to a drift score computed by the other in Grafana: same metric
names (`drift_score`, `drift_detected`), same `feature` label, only `mode`
differs (`batch` vs `streaming`).

| | Batch | Streaming |
|---|---|---|
| Workload | `CronJob`, `batch.schedule` (every 5 min by default) | `Deployment`, one long-running pod |
| Window | Collects a fresh `WINDOW_SECONDS` (60s) of Kafka messages each run, then exits | Keeps a sliding `deque(maxlen=WINDOW_SIZE)` (200 events) in memory, re-checks every `CHECK_INTERVAL_SECONDS` (15s) |
| Feast interaction | None — comparing a bulk window against history isn't a serving-time read | Pushes every consumed event to `02-feature-store`'s online store via `/push`, so a real serving system reading through Feast sees the same events this check does |
| Answers | "Did the last few minutes look like the reference?" | "Is this drifting *right now*?" |

Neither reads from Kafka using the same consumer group, so running both at
once doesn't have them fight over partitions or double-count messages —
batch mode's `auto_offset_reset=latest` + a fresh consumer per run means it
just samples whatever's flowing during its window; it does not guarantee
exactly-once or complete coverage of every message, which is fine for a
drift *sample* but would need addressing before this became anything
correctness-critical.

## Why the reference distribution is generated inline, not read from Feast

A real deployment would pull the reference window from `02-feature-store`'s
offline store (`amount_source`). That needs a working Feast
historical-retrieval call, which — like the rest of stage 2 — hasn't been
run against a live feature server yet. `common/reference_data.py` generates
the same distribution inline instead (seeded, so it's deterministic across
runs), so both drift-check scripts are runnable without depending on a
Feast call this pass didn't get to verify. Swapping it for a real
`get_historical_features()` call once stage 2 is verified is the natural
next step — noted here rather than left implicit.

## Build and install

```bash
# from 03-drift-engine/ — both Dockerfiles need ../common/, so build
# context is this directory, not batch/ or streaming/ themselves
minikube image build -t drift-batch:local -f batch/Dockerfile .
minikube image build -t drift-streaming:local -f streaming/Dockerfile .
helm install drift-engine . -n drift-detection --create-namespace
```

## Related

- [`../README.md`](../README.md) — the full pipeline and the shared-namespace
  cross-chart addressing this chart's `values.yaml` depends on
  (`ingestion-kafka:9092`, `feature-store-feast:6566`,
  `metrics-export-otel-collector:4317`).
- [`../../k8s/k8s_mlops/evidently_stack/`](../../k8s/k8s_mlops/evidently_stack/) —
  the simpler, already-verified single-run Evidently demo this stage's
  Evidently usage is drawn from.
- [`../../../mlops_aiops/docs/tools/evidently/README.md`](../../../mlops_aiops/docs/tools/evidently/README.md),
  [`.../opentelemetry/README.md`](../../../mlops_aiops/docs/tools/opentelemetry/README.md).
