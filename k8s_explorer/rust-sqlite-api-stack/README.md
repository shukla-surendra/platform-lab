# rust-sqlite-api-stack

One Helm chart that deploys **`rust-sqlite-api`** — an OTLP collector for logs,
metrics and traces backed by an embedded SQLite database — together with its own
**Prometheus, Grafana, and dashboards**. `helm install` gives you a running
collector and a Grafana already showing it, with no manual dashboard import.

The image is public: [`surendrashukla29/rust-sqlite-api:0.2.0`](https://hub.docker.com/r/surendrashukla29/rust-sqlite-api)
(multi-arch `amd64` + `arm64`, 6.7 MB pulled). It is built in
[`../../public_docker_images/rust-sqlite-api/`](../../public_docker_images/rust-sqlite-api/) —
that directory owns the image, this one owns everything Kubernetes.

## Install

```bash
helm dependency build          # first time only; fetches the two subcharts

# Cluster with no Loki of its own — deploys Loki + Promtail so the logs
# dashboard has something to query:
helm install rsa . -n observability --create-namespace \
  --set loki-stack.enabled=true

# Cluster that already runs Loki elsewhere — point at it instead:
helm install rsa . -n observability --create-namespace \
  --set externalLoki.url=http://<loki-svc>.<ns>.svc.cluster.local:3100
```

Then:

```bash
kubectl -n observability port-forward svc/rsa-grafana 3000:80
open http://localhost:3000     # admin / admin
```

**In the logs dashboard, set the Namespace variable to the release namespace.**
It defaults to `default`, which is empty, and an empty panel looks identical to
a broken one.

Feed it something:

```bash
kubectl -n observability port-forward svc/rsa-rust-sqlite-api 8080:8080
ENDPOINT=http://localhost:8080 \
  ../../public_docker_images/rust-sqlite-api/testdata/send.sh
```

## What gets created

Seven objects of its own, plus whatever the subcharts bring (106 total by
default, 122 with Loki, 7 with subcharts off):

| Object | Purpose |
|---|---|
| `StatefulSet` | The collector. One replica, one PVC — see below |
| `Service` + headless `Service` | ClusterIP for OTLP ingest; headless for stable per-pod DNS |
| `ServiceMonitor` | Tells Prometheus to scrape `/metrics` every 15s |
| `PrometheusRule` | 6 alerts |
| `ConfigMap` (dashboards) | Both Grafana dashboards, labelled for the sidecar |
| `ConfigMap` (Loki datasource) | Points Grafana at a Loki that already exists |

| Values flag | Default | Effect |
|---|---|---|
| `kube-prometheus-stack.enabled` | `true` | Prometheus + Grafana + CRDs |
| `loki-stack.enabled` | **`false`** | A second Loki. Off because [`../grafana-log-viewer`](../grafana-log-viewer/) already runs one |
| `externalLoki.enabled` | `true` | Registers that existing Loki as a Grafana datasource |

## Dashboards

**`rust-sqlite-api — collector health`** (13 panels, Prometheus). Four rows:
*Is it healthy? · Flow · Loss · Writer*. Reports on the **collector**, not the
telemetry it stores — if the only metrics you export are the ones you were
handed, you cannot tell a quiet system from a broken ingest path.

**`rust-sqlite-api — logs`** (5 panels, Loki). The app logs structured JSON to
stdout, so `| json | level="ERROR"` is a field match rather than a substring
grep. Namespace and level are template variables; `ALL` is the regex `.+` rather
than a literal, so one LogQL matcher serves every choice and no panel needs a
conditional query.

The two are meant to be read together: the health dashboard says *a batch
failed*, the logs dashboard says *why*.

### The three loss panels are not the same thing

This distinction is the health dashboard's main point:

| Panel | Meaning | Data lost? |
|---|---|---|
| **Dropped** | Queue was full, record shed | **Yes** — real loss, by design under overload |
| **Deduped** | `UNIQUE(trace_id, span_id)` rejected a re-delivery | No — a retry correctly absorbed. Rising rate means exporters are timing out |
| **Skipped** | Parsed but unstorable (exponential histogram, summary, span with no ID) | No — never stored, but counted so the gap has an explanation |

Reading all three as "errors" is the mistake the panel descriptions prevent.

Colours are fixed per signal — logs blue `#3B82F6`, metrics amber `#D97706`,
traces violet `#8B5CF6` — assigned by field override so filtering never repaints
a series. Checked with a CVD validator rather than by eye: worst adjacent pair
separates by ΔE 30.2 under protanopia, all six checks pass on light and dark.
Red/amber/green appear only as threshold states, never as a series colour.

Ingest rate and write rate are **two panels, not one chart with two axes**. A
dual-axis chart lets you place any two lines in any relationship by choosing
scales, so the comparison it appears to support is not one you can trust.

## Alerts

| Alert | Fires when | Severity |
|---|---|---|
| `CollectorDown` | target unscrapeable 2m | critical |
| `WriteErrors` | any commit failure in 10m | critical |
| `TelemetryDropping` | >1% of accepted records shed for 10m | warning |
| `WriteQueueSaturated` | queue >80% full for 5m — **fires before drops begin** | warning |
| `WriterSaturated` | >80% of wall clock inside commit for 10m | warning |
| `ExporterRetryStorm` | >25% of spans are re-deliveries for 15m | info |

`WriteQueueSaturated` is the one that earns its keep: acting on it costs
nothing, waiting for `TelemetryDropping` means the data is already gone.

## Decisions that are load-bearing

**`replicaCount` above 1 refuses to render.** Not a warning — `helm template`
fails with an explanation. The database is a file on each pod's own volume, so
extra replicas do not share it: they partition telemetry across N disconnected
databases and a query returns whichever fraction the Service happened to route
to. That failure is intermittent, silent, and expensive to diagnose. A template
error costs seconds.

**StatefulSet, not Deployment.** A Deployment with a PVC defaults to
`RollingUpdate`, which starts the new pod *before* stopping the old — two
processes writing one SQLite file, exactly the corruption case WAL cannot
protect against. You would have to remember `strategy: Recreate` forever, on
every future edit. A StatefulSet never runs two instances of one ordinal, so the
safe behaviour is the default rather than something someone has to know.

**`serviceMonitorSelectorNilUsesHelmValues: false`.** Without it **nothing is
scraped**. kube-prometheus-stack defaults to selecting only ServiceMonitors
carrying its own release label; this chart's ServiceMonitor is its own object,
so the default silently ignores it. Prometheus comes up healthy, the target list
is empty, and every panel reads "No data" with no error anywhere. Same reasoning
for `ruleSelectorNilUsesHelmValues`.

**`ReadWriteOnce`, and RWX would not help.** SQLite's locking assumes a local
filesystem; over NFS it corrupts rather than blocks.

**No CPU limit on the collector.** Throttling the writer converts a latency blip
into queue growth and then into dropped telemetry. Memory *is* capped, because
the ingest queue is bounded and usage is therefore predictable.

**Liveness `/healthz`, readiness `/readyz`.** Liveness deliberately does not
touch the database: a liveness probe that fails on a busy database restarts the
pod, which unlocks nothing and drops every in-flight request. Readiness does
check it — an instance that cannot reach storage should leave the Service, not
be killed.

**etcd / controller-manager / scheduler / kube-proxy scrapes disabled.** On a
single-node minikube those endpoints are unreachable, and every permanently-red
target is noise that makes a real failure harder to spot. Alertmanager is off
for the same reason plus CPU — see [`../docs/incidents.md`](../docs/incidents.md).

**Loki is not deployed by default.** [`../grafana-log-viewer`](../grafana-log-viewer/)
already runs Loki + Promtail in the `log-viewer` namespace, and that install
took a CPU-scheduling fix to get healthy. A second one competes for the same
scarce budget. `externalLoki.url` points at it instead; `loki-stack.enabled=true`
is there for a cluster that has neither.

## Verified

| | |
|---|---|
| `helm lint` | clean |
| `helm dependency build` | both subcharts resolve |
| `helm template` | 106 objects default · 122 with Loki · 7 with subcharts off |
| Replica guard | `--set replicaCount=2` fails with an explanation |
| 16 wiring assertions on rendered YAML | all pass — incl. ServiceMonitor selector matches Service labels, and the logs dashboard's datasource uid matches the ConfigMap's |
| Both dashboards | parse as valid JSON after ConfigMap templating (13 and 5 panels) |
| Dashboards + all PromQL | exercised for real against Prometheus + Grafana via the compose stack in `../../public_docker_images/rust-sqlite-api/deploy/compose/`, including forced drops (7,442 shed, 6.2% ratio) |

**Not verified:** nothing has been applied to a cluster. `minikube` is installed
but was not running, so `helm install`, the sidecar actually discovering the
ConfigMaps, and Prometheus actually scraping the target are all untested here.
That is the next step, and the place this will most likely break first.

## A limitation worth knowing before you trust the dashboard

`telemetry_queue_depth` is a **gauge**, sampled every 15s. A sub-second burst
can fill and drain the queue entirely between two scrapes — saturation reads 0
while `telemetry_dropped_total` climbs. This was observed while testing: 7,442
records dropped with the saturation panel showing zero.

**When diagnosing loss, trust the counters, not the gauge.** Counters cannot
miss an event between scrapes; gauges can and do.
