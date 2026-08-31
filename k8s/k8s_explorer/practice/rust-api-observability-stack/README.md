# rust-api-observability-stack

One Helm chart that deploys **[`rust-api`](https://hub.docker.com/r/surendrashukla29/rust-api)**
— a small, stateless HTTP test server (health check, on-demand log generation,
httpbin-style endpoints, no database, no volume) — together with its own
Prometheus, Grafana, Loki, and dashboards. `helm install` gives you a running
app and a Grafana already showing it: no manual dashboard import.

Image: `surendrashukla29/rust-api:1.0.0`, pinned in `values.yaml` (also
matches `Chart.yaml`'s `appVersion`). Built in
[`../../../../public_docker_images/rust-api/`](../../../../public_docker_images/rust-api/)
— that directory owns the image, this one owns everything Kubernetes.

**Renamed and rewritten.** This chart used to deploy `rust-sqlite-api` — an
OTLP telemetry collector backed by an embedded SQLite database, run as a
StatefulSet with a PersistentVolumeClaim. That app was retired: `rust-api`
is a different, stateless design (see that image's README for what was
removed and why). The chart directory and Helm object names still say
`rust-sqlite-api-stack` — renaming a Helm chart mid-flight risks orphaning
release history more than it's worth for a practice cluster — but every
template, dashboard, and value below now matches the app that actually
ships.

## Install

```bash
helm dependency build          # first time only; fetches the two subcharts

# Everything: the app, Prometheus, Grafana, Loki, Promtail, dashboards.
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
wherever you installed. If you had a dashboard open before an upgrade,
hard-refresh — Grafana remembers your last variable selection per browser,
and a stale one shows an empty panel that looks identical to a broken one.

## Reaching the API

The Service is `NodePort` — **service port 8080, node port 30080**. It
cannot literally *be* 8080: Kubernetes restricts node ports to
`30000-32767` unless `--service-node-port-range` is widened on the
apiserver. The chart fails to render rather than silently accepting an
out-of-range value.

```bash
kubectl -n observability get svc rsa-rust-api
# rsa-rust-api   NodePort   10.99.216.24   <none>   8080:30080/TCP
```

**On minikube with the docker driver (macOS/Windows), the node IP is not
reachable from the host.** Nodes are containers on a private bridge the
host cannot route to, so `http://$(minikube ip):30080` times out even
though the Service is correct.

Pick one:

```bash
# 1. port-forward — gives you a literal localhost:8080. Simplest.
kubectl -n observability port-forward svc/rsa-rust-api 8080:8080

# 2. minikube's own tunnel — prints a URL, then stays in the FOREGROUND.
minikube service rsa-rust-api -n observability --url

# 3. On Linux, or any driver with routable nodes, the node port works directly:
curl http://$(minikube ip):30080/healthz
```

Then:

```
http://localhost:8080/          landing page — every endpoint, live example
http://localhost:8080/version   which binary is actually answering
```

Feed the log pipeline something:

```bash
# Exact count, one level: proves "did every line I asked for arrive".
curl -X POST 'localhost:8080/debug/logstorm?count=500&tag=proof'

# Realistic mixed-level traffic, for exercising dashboards/alerts.
curl -X POST 'localhost:8080/debug/random-logs'
```

`service.type=ClusterIP` on any real cluster. NodePort opens the port on
every node with nothing in front of it, and this API has no authentication.

## Upgrade

**Always repeat every `--set` you installed with.** Helm does not remember
them; a flag you omit reverts to the chart default. Leaving off
`--set loki-stack.enabled=true` silently uninstalls Loki and Promtail, and
the logs dashboard goes empty with nothing to explain why.

```bash
helm upgrade --install rsa . -n observability --create-namespace \
  --set loki-stack.enabled=true

helm upgrade rsa . -n observability --set loki-stack.enabled=true --dry-run
```

### Upgrading a release still on the old `rust-sqlite-api` chart/image

A release installed before the rewrite (nameOverride `rust-sqlite-api`,
image `surendrashukla29/rust-sqlite-api`, `persistence.enabled: true`,
etc.) was very likely installed with `-f` pointing at a full copy of the
old `values.yaml` — `helm get values <release>` shows every key, not a
short delta, when that's the case.

**A plain `helm upgrade rsa .` with no flags will silently reuse that
stored values file** — Helm's default is to carry the previous release's
values forward, not fall back to the new chart's defaults. Verified live
against this chart's own install: a no-flags `--dry-run` upgrade still
rendered `image: surendrashukla29/rust-sqlite-api:1.0.0` — a tag that does
not exist, since that image never published past `0.2.0`. That upgrade
would leave the release in `failed` with an `ImagePullBackOff`.

Force it to adopt the new chart's own defaults instead:

```bash
helm upgrade rsa . -n observability --reset-values

# Confirm first if you want to see the diff before applying:
helm upgrade rsa . -n observability --reset-values --dry-run
```

No extra `--set` flags are needed for this — everything the old install
needed one for (`loki-stack.enabled=true`, the wiring values) is now the
chart's own default.

**The upgrade will likely fail once, on the Service, and that's expected.**
`service.nodePort` is pinned to `30080` in both the old and new chart, and
the old Service is named `rsa-rust-sqlite-api` while the new one is
`rsa-rust-api` — a rename, not an in-place update. Helm creates the new
object before pruning the one that disappeared from the manifest, and two
Services cannot hold the same NodePort at once:

```
Error: UPGRADE FAILED: failed to create resource: server-side apply failed
for object observability/rsa-rust-api /v1, Kind=Service: Service
"rsa-rust-api" is invalid: spec.ports[0].nodePort: Invalid value: 30080:
provided port is already allocated
```

Helm rolls back cleanly on this failure — `helm history` still shows the
previous revision as `deployed`, nothing is left half-applied — but that
also means the old Service is still sitting on the port. Free it by hand,
then retry the same upgrade command:

```bash
kubectl -n observability delete svc rsa-rust-sqlite-api rsa-rust-sqlite-api-headless
helm upgrade rsa . -n observability --reset-values
```

Verified live: this exact sequence (fail on the Service → delete the two
old Services → retry) took the release from revision 21 (old chart, old
image) to revision 23 (`rsa-rust-api` on `surendrashukla29/rust-api:1.0.0`,
`Running`, `/healthz` and `/version` both answering correctly) with no
other manual steps.

**One thing `--reset-values` does not clean up:** the old StatefulSet's
PersistentVolumeClaim. `volumeClaimTemplates` PVCs are created by the
StatefulSet controller directly, not by Helm, so they are not part of the
release manifest and are not pruned when the StatefulSet disappears from
it. Delete it by hand after confirming the new Deployment is up:

```bash
kubectl -n observability get pvc
kubectl -n observability delete pvc data-rsa-rust-sqlite-api-0
```

A values file beats a growing pile of `--set` flags once there is more than
one:

```bash
helm upgrade --install rsa . -n observability -f my-values.yaml
```

Inspect and undo:

```bash
helm history rsa -n observability
helm get values rsa -n observability          # what is actually set right now
helm rollback rsa <REVISION> -n observability
```

### Changes that need a nudge after the upgrade

| Changed | Also run | Why |
|---|---|---|
| `externalLoki.*`, or anything about a datasource | `kubectl -n observability rollout restart deploy rsa-grafana` | Grafana provisions datasources at startup. The sidecar refreshes dashboards live, but **not** datasources |
| `loki-stack.promtail.*` | `kubectl -n observability rollout restart daemonset rsa-promtail` | Promtail reads its config once at boot |
| Dashboard JSON in `dashboards/` | nothing | The sidecar picks these up within ~10s |
| `config.rustLog` | nothing | Handled by the normal Deployment rollout |
| Upgrading from the old `rust-sqlite-api` chart/image | `kubectl -n observability delete pvc data-rsa-rust-sqlite-api-0` (one time) | The StatefulSet's PVC isn't Helm-tracked, so it survives the StatefulSet being pruned |

## What gets created

Six objects of its own, plus whatever the subcharts bring:

| Object | Purpose |
|---|---|
| `Deployment` | The app. Stateless, `replicaCount` can be anything |
| `Service` | ClusterIP/NodePort for HTTP |
| `ServiceMonitor` | Off by default — rust-api has no `/metrics` endpoint |
| `PrometheusRule` | Off by default — 3 pod-level alerts (down, crash-looping, near memory limit) |
| `ConfigMap` (dashboards) | Both Grafana dashboards, labelled for the sidecar |
| `ConfigMap` (Loki datasource) | Only when `externalLoki.enabled=true` |

| Values flag | Default | Effect |
|---|---|---|
| `kube-prometheus-stack.enabled` | `true` | Prometheus + Grafana + the ServiceMonitor/PrometheusRule CRDs |
| `loki-stack.enabled` | `true` | Loki + Promtail, and a Grafana datasource pointing at them |
| `externalLoki.enabled` | `false` | Only for reusing a Loki this chart did **not** deploy. Pair with `loki-stack.enabled=false` |
| `service.type` / `service.nodePort` | `NodePort` / `30080` | See [Reaching the API](#reaching-the-api). `ClusterIP` on any real cluster |
| `config.heartbeatSecs` | `30` | Seconds between `alive` log lines |
| `replicaCount` | `1` | Can be raised freely — no shared state to fragment |

## How logs actually reach Grafana

**The application pushes nothing.** It writes structured JSON to stdout and
stops there. Everything after that is someone else's job:

```
 rust-api pod
   │  tracing-subscriber writes JSON to stdout
   ▼
 container runtime (docker on this cluster)
   │  wraps each line: {"log":"…","stream":"stdout","time":"…"}
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
```

The five things that must all hold — pod carries a plain `app` label, the
runtime-unwrap pipeline stage matches the actual runtime, the Promtail push
URL is pinned to `<release>-loki` rather than the upstream default, the
datasource uid is pinned to `loki`, and the app actually logs something at
the configured level — are exactly the same five as before and are still
wired the same way in `values.yaml` and `templates/deployment.yaml`.

## How "metrics" work without a `/metrics` endpoint

`rust-api` is a sample API-testing target, not an instrumented service — it
exposes no Prometheus metrics. The **health & requests** dashboard is built
from two sources that need zero setup on the app's part:

- **Pod-level metrics** (CPU, memory, restarts) — from cAdvisor and
  kube-state-metrics, already scraped by kube-prometheus-stack for every pod
  on the cluster. Selected by `container="rust-api"`, not by a
  release-specific job name, so this keeps working across reinstalls.
- **Request-level activity** (rate, status-code breakdown) — computed from
  tower_http's per-request access-log lines via LogQL, in Grafana panels,
  not from Prometheus at all. This needs `RUST_LOG` to include
  `tower_http=debug`, which `config.rustLog` sets by default.

A ServiceMonitor pointed at `:8080/metrics` would 404 forever, so it stays
off (`serviceMonitor.enabled: false`). The template still exists — flip it
on if a future version of the app ever adds a real `/metrics` endpoint.

## Dashboards

**`rust-api — health & requests`** (8 panels). Two rows: pod health
(Prometheus/cAdvisor) and request activity (Loki/LogQL). Meant to answer
"is the pod itself okay" and "what's actually hitting it" without needing
the app to export anything.

**`rust-api — logs`** (5 panels, Loki). The app logs structured JSON to
stdout, so `| json | level="ERROR"` is a field match rather than a
substring grep. Namespace and level are template variables; `ALL` is the
regex `.+` rather than a literal, so one LogQL matcher serves every choice.

The two are meant to be read together: the health dashboard says *what
changed*, the logs dashboard says *why*.

### Proving the log pipeline end to end

```bash
curl -X POST 'localhost:8080/debug/logstorm?count=500&tag=proof'
```

```json
{ "requested": 500, "emitted": 300, "suppressed_by_log_level": 200,
  "verify": "sum(count_over_time({app=\"rust-api\"} |= \"proof\" | json | fields_kind=\"synthetic\" [5m]))" }
```

Run the `verify` query in Grafana Explore. It should return **`emitted` +
1** (the extra line is the completion message). Compare against `emitted`,
never `requested`: `RUST_LOG` suppresses lines before they are ever
written, and counting those as lost sends you hunting a pipeline problem
that does not exist. `fields_kind`, not `kind` — `tracing` nests custom
fields under `fields`, and Loki's `| json` flattens nested objects with an
underscore.

### Why the heartbeat exists

The app logs `alive` every `config.heartbeatSecs` (default 30) at INFO,
with uptime and a request count. Without it, "healthy and quiet" and
"wedged" produce identical log output — an empty panel proves nothing
either way. With it, absence of the line is *evidence*.

## Decisions that are load-bearing

**Deployment, not StatefulSet.** rust-api has no database and no shared
state between replicas, so nothing needs ordinal identity or serialized
rollout. `replicaCount` can be raised freely; a Deployment with N replicas
behind the Service just works.

**`serviceMonitorSelectorNilUsesHelmValues: false`.** Without it Prometheus
would ignore any ServiceMonitor this chart *did* create, since
kube-prometheus-stack defaults to selecting only ServiceMonitors carrying
its own release label. Currently moot (the ServiceMonitor is off by
default), but load-bearing the moment it's turned on.

**Loki is not deployed by default outside this chart's own subchart.**
`loki-stack.enabled=true` ships one bundled with this release;
`externalLoki.url` exists for reusing one that already runs elsewhere (e.g.
[`../grafana-log-viewer`](../grafana-log-viewer/)) instead of running a
second Loki competing for the same CPU budget.

**loki-stack's `isDefault: false`.** That subchart ships its own Grafana
datasource ConfigMap and marks it default by upstream default — but
kube-prometheus-stack's Prometheus datasource is *also* default, and
Grafana refuses to start with two ("only one datasource per organization
can be marked as default"). Pinned off in `values.yaml`.

**Pod carries a plain `app` label, not just `app.kubernetes.io/name`.**
loki-stack's Promtail keys pod discovery off `app` or `name` and silently
drops pods carrying neither. A pod with only the modern label set never
appears in Loki, and the logs dashboard is empty for a reason that looks
nothing like a labelling problem.

**Promtail's push URL is pinned to `<release>-loki`.** The upstream
loki-stack default assumes the Loki Service is named exactly the release,
but the Loki subchart names it `<release>-loki`. With the default,
Promtail stays `1/1 Running` and posts every batch into the void.

**No CPU limit on the app.** It is a stateless HTTP handler; there is
nothing here that benefits from being throttled rather than just given
more cycles when available.

## What's verified, and what isn't

| | |
|---|---|
| `helm dependency build`, `helm lint`, `helm template` | clean — 118 objects, no errors, `replicaCount=3` renders fine now (the old chart's StatefulSet refused above 1) |
| Live upgrade path | reproduced on this cluster's actual `rsa` release: `helm upgrade --reset-values` fails once on the renamed Service (NodePort collision, rolls back cleanly), then succeeds after deleting the two old Services — see [Upgrade](#upgrade) |
| Deployment rollout | `rsa-rust-api` `Running`, `/healthz` and `/version` both answering (`version: 1.0.0`) |
| Log pipeline, end to end, via Loki's HTTP API directly | `app="rust-api"` present in Loki's label set; `fields_status=~".+"` query returned real counts; `|= "alive"` heartbeat query returned `3` over ~90s of traffic (in line with `HEARTBEAT_SECS=30`); the logstorm proof query (`count=3&tag=...`) returned `4` — 3 storm lines + 1 completion line, exactly the documented `emitted + 1` |
| Raw pod log format (`kubectl logs`) | `level` is top-level JSON; `message`, `status`, `kind`, `latency` all nest under `fields` (flatten to `fields_message`, `fields_status`, `fields_kind`, `fields_latency` after Loki's `\| json`) — confirms the field-flattening claims elsewhere in this doc |

**One thing this confirmed rather than merely justified:** `latency` is
logged as a string with an embedded unit, e.g. `"0 ms"` — not a bare
number. A LogQL `\| unwrap fields_latency` panel would fail to parse that
without a regex to strip the unit first, which is why no numeric latency
panel shipped in the health & requests dashboard — that omission was a
guess before this pass, and is now a confirmed constraint.

**Still not verified:** the Grafana UI itself — panels rendering as
expected, variable dropdowns behaving, colors matching descriptions — since
this pass queried Loki's API directly rather than opening a browser. The
underlying queries are now known to return real data; whether they render
the way each panel's `fieldConfig` intends is the next thing to eyeball.
