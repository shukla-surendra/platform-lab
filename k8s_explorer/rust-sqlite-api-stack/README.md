# rust-sqlite-api-stack

One Helm chart that deploys **`rust-sqlite-api`** — an OTLP collector for logs,
metrics and traces backed by an embedded SQLite database — together with its own
**Prometheus, Grafana, and dashboards**. `helm install` gives you a running
collector and a Grafana already showing it, with no manual dashboard import.

The image is public: [`surendrashukla29/rust-sqlite-api`](https://hub.docker.com/r/surendrashukla29/rust-sqlite-api)
— `0.2.0` on Docker Hub (multi-arch `amd64` + `arm64`, 6.7 MB pulled). `0.4.0`,
which adds the heartbeat, `/debug/logstorm`, and the API-testing surface, exists
locally and in minikube but is **not pushed yet**; the chart's `appVersion`
still points at `0.2.0`, so override with `--set image.tag=0.4.0` to run it.
It is built in
[`../../public_docker_images/rust-api/`](../../public_docker_images/rust-api/)
(renamed from `rust-sqlite-api`, and rewritten to a stateless design in its own
`1.0.0` — this chart still deploys the pre-rewrite `0.2.0`/`0.4.0` image and has
not been updated for the rename or the rewrite; see that image's `CHANGELOG.md`) —
that directory owns the image, this one owns everything Kubernetes.

## Install

```bash
helm dependency build          # first time only; fetches the two subcharts

# Everything: the collector, Prometheus, Grafana, Loki, Promtail, dashboards.
helm install rsa . -n observability --create-namespace

# Cluster that already runs Loki elsewhere — reuse it instead of deploying one:
helm install rsa . -n observability --create-namespace \
  --set loki-stack.enabled=false \
  --set externalLoki.enabled=true \
  --set externalLoki.url=http://<loki-svc>.<ns>.svc.cluster.local:3100
```

Then:

```bash
kubectl -n observability port-forward svc/rsa-grafana 3000:80
open http://localhost:3000     # admin / admin
```

The logs dashboard's Namespace variable defaults to **All**, so it works
wherever you installed. If you had the dashboard open before an upgrade,
hard-refresh — Grafana remembers your last variable selection per browser, and a
stale one shows an empty panel that looks identical to a broken one.

## Reaching the API

The Service is `NodePort` — **service port 8080, node port 30080**. It cannot
literally *be* 8080: Kubernetes restricts node ports to `30000-32767` unless
`--service-node-port-range` is widened on the apiserver. The chart fails to
render rather than silently accepting an out-of-range value.

```bash
kubectl -n observability get svc rsa-rust-sqlite-api
# rsa-rust-sqlite-api   NodePort   10.99.216.24   <none>   8080:30080/TCP
```

**On minikube with the docker driver (macOS/Windows), the node IP is not
reachable from the host.** Nodes are containers on a private bridge that the
host cannot route to, so `http://$(minikube ip):30080` times out even though
the Service is correct — verified working from *inside* the cluster against all
three node IPs. This surprises people because `kubectl get svc` looks perfect.

Pick one:

```bash
# 1. port-forward — gives you a literal localhost:8080. Simplest, and the
#    ClusterIP path, so it also works on a cluster with no NodePort at all.
kubectl -n observability port-forward svc/rsa-rust-sqlite-api 8080:8080

# 2. minikube's own tunnel — prints a URL, then stays in the FOREGROUND.
#    Run it in its own terminal; backgrounding it in a script will look like
#    a hang.
minikube service rsa-rust-sqlite-api -n observability --url

# 3. On Linux, or any driver with routable nodes, the node port works directly:
curl http://$(minikube ip):30080/healthz
```

Then:

```
http://localhost:8080/          landing page — every endpoint, with a live try-it
http://localhost:8080/version   which binary is actually answering
http://localhost:8080/metrics   Prometheus text
```

`service.type=ClusterIP` on any real cluster. NodePort opens the port on every
node with nothing in front of it, and this API has no authentication.

Feed it something:

```bash
# testdata/send.sh no longer exists — it sent OTLP payloads, and the deployed
# image's 1.0.0 successor has no OTLP ingest to receive them. Left here as a
# marker of what needs rewriting alongside the rest of this chart.
ENDPOINT=http://localhost:8080 \
  ../../public_docker_images/rust-api/testdata/send.sh

# prove the log pipeline end to end: emits a known count, tells you the LogQL
# to compare against Loki
curl -X POST 'localhost:8080/debug/logstorm?count=500&tag=proof'
```

## Upgrade

**Always repeat every `--set` you installed with.** Helm does not remember them;
a flag you omit reverts to the chart default. Leaving off
`--set loki-stack.enabled=true` silently uninstalls Loki and Promtail, and the
logs dashboard goes empty with nothing to explain why.

```bash
# The everyday one. --install makes it idempotent, so the same command works
# whether or not the release exists yet.
helm upgrade --install rsa . -n observability --create-namespace \
  --set loki-stack.enabled=true

# Preview the change before applying it
helm upgrade rsa . -n observability --set loki-stack.enabled=true --dry-run

# Diff against what is live (needs: helm plugin install https://github.com/databus23/helm-diff)
helm diff upgrade rsa . -n observability --set loki-stack.enabled=true
```

A values file beats a growing pile of `--set` flags once there is more than one:

```bash
helm upgrade --install rsa . -n observability -f my-values.yaml
```

After a chart-version or dependency bump:

```bash
helm dependency build      # refresh charts/ from Chart.lock first
helm upgrade --install rsa . -n observability --set loki-stack.enabled=true
```

Inspect and undo:

```bash
helm history rsa -n observability
helm get values rsa -n observability          # what is actually set right now
helm rollback rsa <REVISION> -n observability
```

### Changes that need a nudge after the upgrade

Helm updates the objects; some workloads do not notice. Each of these was hit
during the first real install of this chart:

| Changed | Also run | Why |
|---|---|---|
| Anything in the app pod spec, while the pod is **CrashLoopBackOff** | `kubectl -n observability delete pod rsa-rust-sqlite-api-0` | A StatefulSet rolling update waits for the current pod to be Ready before replacing it. An unhealthy pod stalls its own fix forever |
| `externalLoki.*`, or anything about a datasource | `kubectl -n observability rollout restart deploy rsa-grafana` | Grafana provisions datasources at startup. The sidecar refreshes dashboards live, but **not** datasources |
| `loki-stack.promtail.*` | `kubectl -n observability rollout restart daemonset rsa-promtail` | Promtail reads its config once at boot |
| Dashboard JSON in `dashboards/` | nothing | The sidecar picks these up within ~10s |
| `config.rustLog` | nothing | Handled by the normal StatefulSet rollout |

Then confirm the roll actually completed rather than assuming:

```bash
kubectl -n observability rollout status statefulset/rsa-rust-sqlite-api
kubectl -n observability get pods
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
| `kube-prometheus-stack.enabled` | `true` | Prometheus + Grafana + the ServiceMonitor/PrometheusRule CRDs |
| `loki-stack.enabled` | `true` | Loki + Promtail, and a Grafana datasource pointing at them |
| `externalLoki.enabled` | `false` | Only for reusing a Loki this chart did **not** deploy — e.g. [`../grafana-log-viewer`](../grafana-log-viewer/). Pair with `loki-stack.enabled=false` |
| `service.type` / `service.nodePort` | `NodePort` / `30080` | See [Reaching the API](#reaching-the-api). `ClusterIP` on any real cluster |
| `config.persistTelemetry` | `true` | `false` makes it a pure OTLP sink — counted and discarded, never written |
| `config.heartbeatSecs` | `30` | Seconds between `alive` log lines |

`loki-stack.enabled` defaults **on** deliberately. Half of "see your collector"
is logs, and defaulting it off produced an empty logs dashboard on a fresh
install with nothing to explain why — plus a `helm upgrade -f values.yaml` that
silently uninstalled Loki for anyone who had enabled it with `--set`.

## How logs actually reach Grafana

**The application pushes nothing.** It has no Loki client, no log file, and no
idea Loki exists. It writes structured JSON to stdout and stops there.
Everything after that is someone else's job:

```
 rust-sqlite-api pod
   │  tracing-subscriber writes JSON to stdout
   ▼
 container runtime (docker on this cluster)
   │  wraps each line: {"log":"…","stream":"stdout","time":"…"}
   │  writes /var/log/pods/<ns>_<pod>_<uid>/<container>/0.log on THAT node
   ▼
 Promtail  ← DaemonSet: one pod per node, reads the node's log files
   │  discovers pods via the k8s API, keeps those with an `app` or `name` label
   │  pipeline stage `docker: {}` unwraps the runtime envelope
   │  attaches labels: app, namespace, pod, container, node_name, job
   │  POSTs to http://<release>-loki:3100/loki/api/v1/push
   ▼
 Loki      ← StatefulSet: stores and indexes by label
   ▼
 Grafana   ← queries Loki through the `loki` datasource (uid must be "loki")
              dashboard panels run LogQL against it
```

Five things must all hold, and **every one of them failed at least once** on
the first real install of this chart:

| Link | Fails when | What you see |
|---|---|---|
| The app logs at all | `RUST_LOG=info` and the app only logs on error | Empty panel. Nothing is broken — there is genuinely nothing to show |
| Promtail runs on the app's node | DaemonSet not scheduled there | Logs from other pods appear; this one never does |
| Promtail *selects* the pod | Pod has no plain `app`/`name` label | Pod never appears in Loki at all, silently |
| The unwrap stage matches the runtime | `cri: {}` on a Docker cluster | Lines arrive and look fine, but `| json` parses the WRAPPER — `level` is always empty |
| Datasource uid matches the dashboard | Grafana generated its own uid | Every panel empty, no error shown |

Note the shape of those failures: **four of the five produce silence, not an
error.** Promtail stays `1/1 Running` throughout. That is why this chart pins
the label, the pipeline stage, the push URL, and the datasource uid explicitly
in `values.yaml` rather than trusting defaults.

### Proving the chain, end to end

Guessing is expensive here. `0.4.0` of the image ships an endpoint that emits a
known number of lines and tells you exactly how many to expect:

```bash
curl -X POST 'localhost:8080/debug/logstorm?count=500&tag=proof'
```

```json
{ "requested": 500, "emitted": 300, "suppressed_by_log_level": 200,
  "verify": "sum(count_over_time({app=\"rust-sqlite-api\"} |= \"proof\" | json | fields_kind=\"synthetic\" [5m]))" }
```

Run the `verify` query in Grafana Explore. It should return **`emitted` + 1**
(the extra line is the completion message). Measured on this cluster:
**301 emitted, 301 in Loki — exact.**

Compare against `emitted`, never `requested`: `RUST_LOG` suppresses lines before
they are ever written, and counting those as lost sends you hunting a pipeline
problem that does not exist.

Two details make that query exact rather than approximate:

- **`fields_kind`, not `kind`.** `tracing` nests custom fields under `fields`,
  and Loki's `| json` flattens nested objects with an underscore. Filtering on
  `kind` matches nothing and reports zero — which reads as total loss.
- **The `kind` filter at all.** A bare `|= "proof"` also matches `tower_http`'s
  request lines, because they echo the URI and the tag is in the query string.
  That over-counts by three and reads as duplication.

### Why the heartbeat exists

The app logs `alive` every `config.heartbeatSecs` (default 30) at INFO, with
uptime and counters. It is not decoration:

- Without it, **"healthy and quiet" and "wedged" produce identical output** —
  an empty panel proves nothing either way.
- With it, absence of the line is *evidence*, which is the only thing that makes
  an empty log panel actionable.
- It gives the pipeline a steady input, so Promtail, Loki, and the dashboard can
  be seen working before there is any real traffic to look at.

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

## What broke on the first real install

Nine distinct failures between `helm install` and a working logs dashboard.
Every fix is baked into `values.yaml` or the templates, each with a comment at
the site of the fix, so a fresh install hits none of them. Recorded here because
the *shape* of these is more transferable than the fixes.

| # | Failure | Symptom | Fix |
|---|---|---|---|
| 1 | `fsGroup` is ignored on hostPath volumes — minikube's default `standard` StorageClass | App CrashLoopBackOff, `SQLITE_CANTOPEN` on a volume that is mounted and looks fine | `persistence.fixOwnership` init container chowns `/data` |
| 2 | That init container ran `chown` then `chmod` | `chmod: Operation not permitted` — the chown drops root's ownership, so chmod then needs `FOWNER`, which was dropped | Removed the chmod. Ownership was the only requirement |
| 3 | loki-stack's Promtail defaults to `http://<release>:3100` | Promtail `1/1 Running`, posting into the void. Loki holds zero streams | Pin `promtail.config.clients[0].url` to `<release>-loki` |
| 4 | Pod carried only `app.kubernetes.io/name` | Promtail **drops** pods with no plain `app`/`name` label. Logs never collected at all | Added `app:` to the pod template |
| 5 | Promtail used `cri: {}` on a Docker runtime | Lines arrive and look correct, but `\| json` parses the runtime wrapper — `level` always empty, "Error lines" permanently 0 | `pipelineStages: [docker: {}]` |
| 6 | loki-stack ships a Loki datasource with `isDefault: true`, colliding with Prometheus | **Grafana CrashLoopBackOff**: "only one datasource per organization can be marked as default" | `loki.isDefault: false`, `datasource.uid: loki` |
| 7 | `helm upgrade -f values.yaml` baked the whole file in as user values | A later upgrade silently **uninstalled Loki and Promtail** | `loki-stack.enabled` now defaults `true`; recover with `--reset-values` |
| 8 | App logged 2 lines total — `tower_http` traces at DEBUG, `RUST_LOG=info` | Empty dashboard. Accurate, not broken | `rustLog: info,tower_http=debug` + the heartbeat |
| 9 | Dashboard's `namespace` variable hardcoded to `default` | Every panel empty on any install using a different namespace | `includeAll` + regex match, defaults to All |

### The pattern worth extracting

**Seven of the nine were silent.** No crash, no error log, no failed probe —
just absence. The two that were loud (#1, #6) were fixed in minutes; the silent
ones took the rest of the session.

Three habits fall out of that, and they generalise well beyond this chart:

1. **Check the thing exists before debugging why it isn't arriving.** After
   fixing five delivery bugs, a sixth delivery bug was the obvious hypothesis
   for #8 — but the source was silent. `kubectl logs | wc -l` would have said so
   in two seconds.
2. **`helm get values <release>` first**, whenever a release does not match the
   chart you are reading. #7 was invisible in every template and manifest; one
   command showed `enabled: false` immediately.
3. **Distrust the measuring instrument as much as the system.** The reference
   count in `/debug/logstorm` was wrong three times — over-reporting suppressed
   lines, then over-matching `tower_http`, then under-matching on a flattened
   field name — before it could be trusted to tell the truth about the pipeline.

## Verified

| | |
|---|---|
| `helm lint` | clean |
| `helm dependency build` | both subcharts resolve |
| `helm template` | 106 objects default · 122 with Loki · 7 with subcharts off |
| Replica guard | `--set replicaCount=2` fails with an explanation |
| 16 wiring assertions on rendered YAML | all pass — incl. ServiceMonitor selector matches Service labels, and the logs dashboard's datasource uid matches the ConfigMap's |
| Both dashboards | parse as valid JSON after ConfigMap templating (13 and 5 panels) |
| Dashboards + all PromQL | every panel query returns data against live Prometheus, including forced drops (7,442 shed, 6.2% drop ratio) and dedupes |
| Logs end to end | `/debug/logstorm` emitted 301 lines, Loki returned 301 — exact |
| Deployed on a real cluster | `helm install` on 3-node minikube; app, Prometheus, Grafana, Loki, Promtail all Running |

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
