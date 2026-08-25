# streaming-drift-detection

A five-stage MLOps pipeline for detecting data/prediction drift on a
production-like event stream, scaffolded as five independently-deployable
pieces under this directory — one per stage, mirroring the
one-concern-per-chart split the sibling charts in
[`k8s_observability/`](../README.md) already use, but wired together (they
have to be, this is a pipeline, not three isolated signal demos).

**Status: scaffolded, not yet installed on this repo's minikube cluster.**
Unlike `metrics-stack/`, `log-stack/`, `trace-stack/` (each verified against
a real install), nothing here has been `helm install`ed or run against a live
cluster yet — chart dependency versions and repos below were checked live
against Artifact Hub/GitHub as of 2026-08-25, but the values.yaml keys they're
paired with have not been. Each stage's own README says exactly how far it
got. Treat this as the map + first real code, not a working system yet.

| # | Stage | Dir | Tech | Role |
|---|---|---|---|---|
| 1 | Data Ingestion | [`01-ingestion/`](01-ingestion/) | Kafka | synthetic producer emits "production" events onto a topic — stand-in for Kafka/Pub/Sub/Kinesis, Kafka picked because it's the only one of the three that's realistically self-hostable on minikube |
| 2 | Feature Store / Preprocessing | [`02-feature-store/`](02-feature-store/) | Feast | defines the transformation once, serves it two ways (batch offline + streaming push to online store) so training and serving can't drift apart from each other |
| 3 | Drift Detection Engine | [`03-drift-engine/`](03-drift-engine/) | Evidently + custom stats | the batch/streaming experimentation lives here — one CronJob (scheduled, compares an accumulated window) and one long-running consumer (checks a sliding window continuously), sharing one reference dataset and one metrics-emission path |
| 4 | Metrics Export | [`04-metrics-export/`](04-metrics-export/) | Prometheus + OpenTelemetry | OTel Collector receives drift metrics over OTLP from stage 3, exports them in Prometheus format; Prometheus scrapes and stores them |
| 5 | Dashboards & Alerts | [`05-dashboards-alerts/`](05-dashboards-alerts/) | Grafana + Alertmanager | drift dashboards, and alert rules that fire when a feature's drift score crosses threshold |

## Data flow

```
 ┌─────────────┐   topic: events   ┌──────────────────┐   push API   ┌───────────────────┐
 │ 01-ingestion │ ─────────────────▶│ 02-feature-store  │──────────────▶│                    │
 │ Kafka +      │                   │ Feast:            │              │  03-drift-engine   │
 │ synthetic    │                   │ - offline FileSrc │              │                    │
 │ producer     │                   │   (batch backfill)│   pull (feast│  batch: CronJob    │
 └─────────────┘                   │ - online PushSrc  │   get_online_ │  streaming: consumer│
                                     │   (streaming)     │   features)  │  vs. reference set  │
                                     └──────────────────┘◀─────────────┴─────────┬──────────┘
                                                                                   │ OTLP metrics
                                                                                   ▼
                                                                    ┌───────────────────────┐
                                                                    │  04-metrics-export     │
                                                                    │  OTel Collector        │
                                                                    │  → Prometheus exporter │
                                                                    │  Prometheus scrapes it │
                                                                    └───────────┬───────────┘
                                                                                │ PromQL
                                                                                ▼
                                                                    ┌───────────────────────┐
                                                                    │ 05-dashboards-alerts   │
                                                                    │ Grafana (dashboards)   │
                                                                    │ Alertmanager (routing) │
                                                                    └───────────────────────┘
```

## Why this doesn't reuse `metrics-stack`'s Prometheus/Grafana

The sibling charts deliberately keep one Grafana per signal so no chart has
to reconcile two subcharts fighting over `isDefault`/datasource UIDs (see
[`../README.md`](../README.md#why-one-signal-per-chart-not-one-combined-chart)).
This project applies the same instinct at a different boundary: it's one
coupled system end-to-end (a broken Kafka topic name breaks stage 3, a
renamed metric breaks stage 5's dashboards), so it gets its **own**
Prometheus/Alertmanager/Grafana rather than bolting onto `metrics-stack`'s.
The cost is a second Prometheus and a second Grafana running on the same
cluster; the benefit is this whole pipeline can be `helm install`ed and
`helm uninstall`ed as a unit without touching (or being touched by) the
observability charts next door.

## Why one shared namespace, not five

`metrics-stack`/`log-stack`/`trace-stack` each get their own namespace
because they're unrelated demos that happen to live in the same repo. These
five stages aren't unrelated — stage 3 needs stage 1's Kafka bootstrap
address, stage 2's feature server, and stage 4's OTel Collector endpoint all
at once. Installing all five into one namespace (`drift-detection`) means
those addresses are plain short Service DNS names (`ingestion-kafka:9092`,
not a namespace-qualified FQDN) and nothing has to be re-templated per
namespace. The tradeoff mirrors the "cross-release label collision" bug
`metrics-stack/README.md` documents from the three-chart setup — every
resource here follows that same fix (`release: {{ .Release.Name }}` on
every selector) preemptively, since five releases sharing one namespace
makes that collision far more likely, not less.

## Batch vs. streaming: where "the experimentation" actually lives

Both modes are two deployables of the **same** `03-drift-engine` chart, not
two parallel pipelines — see
[`03-drift-engine/README.md`](03-drift-engine/README.md) for the detail.
Short version: `batch.enabled` runs a `CronJob` that pulls an accumulated
window and compares it to a fixed reference dataset on a schedule (good for
"did today look like last week"); `streaming.enabled` runs a long-lived
Kafka consumer that keeps a sliding in-memory window and re-checks it
continuously (good for "is this happening right now"). Both share the same
reference-dataset logic and the same OTLP metrics emitter in
[`03-drift-engine/common/`](03-drift-engine/common/), so a drift check
computed once in batch mode and again in streaming mode is directly
comparable in Grafana — same metric names, same labels, only `mode` differs.

## Install order (once each stage is filled in past scaffold)

```bash
kubectl create namespace drift-detection

cd 01-ingestion  && helm dependency build . && helm install ingestion . -n drift-detection
cd ../02-feature-store && helm dependency build . && helm install feature-store . -n drift-detection
cd ../03-drift-engine  && helm install drift-engine . -n drift-detection
cd ../04-metrics-export && helm dependency build . && helm install metrics-export . -n drift-detection
cd ../05-dashboards-alerts && helm dependency build . && helm install dashboards-alerts . -n drift-detection
```

Order matters one-way only: each stage's values reference the *previous*
stage's release name (e.g. stage 3's `values.yaml` expects a Kafka reachable
at `ingestion-kafka:9092` and a Feast feature server at
`feature-store-feast:6566`), so install low-numbered stages first. Nothing
later blocks earlier stages from coming up.

## Related

- [`../README.md`](../README.md) — the three-chart signal split
  (`metrics-stack`/`log-stack`/`trace-stack`) this project deliberately
  diverges from, and why.
- [`../../k8s_mlops/evidently_stack/`](../../k8s_mlops/evidently_stack/) —
  the earlier, simpler single-chart Evidently demo (server + Jupyter client)
  that `03-drift-engine`'s batch mode builds on.
- [`../../mlops_aiops/docs/tools/kafka/README.md`](../../mlops_aiops/docs/tools/kafka/README.md),
  [`.../feast/README.md`](../../mlops_aiops/docs/tools/feast/README.md),
  [`.../evidently/README.md`](../../mlops_aiops/docs/tools/evidently/README.md),
  [`.../opentelemetry/README.md`](../../mlops_aiops/docs/tools/opentelemetry/README.md),
  [`.../prometheus/README.md`](../../mlops_aiops/docs/tools/prometheus/README.md),
  [`.../grafana/README.md`](../../mlops_aiops/docs/tools/grafana/README.md) —
  what each tool is and how it compares to the alternatives named in the
  original 5-stage spec (Pub/Sub, Kinesis, Tecton).
