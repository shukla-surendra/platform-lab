# metrics-stack

A thin wrapper chart around the upstream `prometheus-community/kube-prometheus-stack`
chart, tuned for this repo's local `minikube` cluster. One `helm install` gives you all
three pieces of a metrics pipeline together:

1. **A demo app** (`quay.io/brancz/prometheus-example-app`) exposing a real
   `/metrics` endpoint — `templates/demo-app-*.yaml`.
2. **Prometheus**, scraping it via a `ServiceMonitor` (plus node-exporter and
   kube-state-metrics for cluster/node/pod metrics that need no app involvement at all).
3. **Grafana**, pre-wired to that Prometheus as a datasource.

Metrics only — no Loki, no Promtail, no Alertmanager routing. For logs, see
[`../../k8s/k8s_explorer/grafana-log-viewer/`](../../k8s/k8s_explorer/grafana-log-viewer/)
instead — a separate chart, kept separate deliberately (see
[`../../README.md`](../../README.md#why-a-separate-chart-from-grafana-log-viewer)).

## Where this is installed

- **Cluster:** `minikube` profile
- **Namespace:** `metrics` (dedicated, so it can be installed/removed as one unit)
- **Release name:** `metrics`
- **Method:** local chart wrapping `prometheus-community/kube-prometheus-stack`
  (Helm), not raw manifests/kustomize

## Install

Run from inside this directory (`metrics-stack/`) — chart path is `.`:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm dependency build .   # first time only; fetches kube-prometheus-stack into charts/

helm install metrics . \
  --namespace metrics \
  --create-namespace
```

`helm` needs a literal filesystem path (`.`, `./metrics-stack`, `../metrics-stack`) —
running from the repo root, point at the directory: `helm install metrics
k8s/k8s_observability/metrics-stack ...`.

Install brings in Custom Resource Definitions (`ServiceMonitor`, `PodMonitor`,
`PrometheusRule`, etc.) cluster-wide, shared with any other chart on this cluster that
also depends on `kube-prometheus-stack` — e.g.
[`rust-api-observability-stack`](../../k8s/k8s_explorer/rust-api-observability-stack/).
Installing this chart a second time under a different release name will try to
recreate the same CRDs and fail; only one `kube-prometheus-stack`-based release should
run per cluster.

## Upgrade

```bash
helm dependency build .   # only if Chart.yaml's dependency version changed
helm upgrade metrics . --namespace metrics

# or, idempotent either way:
helm upgrade --install metrics . --namespace metrics --create-namespace
```

**Always repeat every `--set` you installed with** — Helm does not remember them; an
omitted flag reverts to the chart default.

## Access Grafana

```bash
kubectl get pods -n metrics -l app.kubernetes.io/name=grafana
minikube service metrics-grafana -n metrics --url
# or: kubectl -n metrics port-forward svc/metrics-grafana 3000:80
```

Login: `admin` / `admin` (set via `values.yaml` — change before using anywhere beyond
local practice). The Prometheus datasource is auto-provisioned
(`sidecar.datasources.enabled: true` in `values.yaml`), so dashboards work immediately.

## View metrics

**Dashboards** — `defaultDashboardsEnabled: true` ships a set of upstream dashboards
with no import step: open Grafana → **Dashboards** and look under the **Kubernetes**
and **Node Exporter** folders for cluster/node/pod panels (CPU, memory, restarts,
deployment status) that work with zero application instrumentation.

**Explore / ad-hoc PromQL** — go to **Explore**, pick the **Prometheus** datasource,
and query directly, e.g.:

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="metrics"}[5m])) by (pod)
```

**Prometheus UI itself** (target list, raw PromQL):

```bash
kubectl -n metrics port-forward svc/prometheus-operated 9090:9090
open http://localhost:9090/targets
```

`prometheus-operated` is a fixed Service name the Prometheus Operator itself creates in
every namespace it runs a Prometheus in — unlike this chart's own
`<release>-kube-promethe-prometheus` Service, whose name gets truncated by Helm's
fullname template to fit the 63-char DNS limit at a point that depends on release-name
length (`app.kubernetes.io/name=prometheus` is **not** a label this chart's own
Prometheus Service actually carries — don't rely on it). `prometheus-operated` works
regardless of release name, verified live against this chart's install.

## The demo app

`demoApp.enabled: true` (default) deploys `quay.io/brancz/prometheus-example-app` — the
minimal app the `prometheus-operator` project's own getting-started docs use for
exactly this purpose. It exposes exactly one real metric:

```
# HELP version Version information about this binary
# TYPE version gauge
version{version="v0.5.0"} 1
```

```bash
kubectl -n metrics port-forward svc/metrics-demo-app 8080:8080
curl http://localhost:8080/metrics
```

The `templates/demo-app-servicemonitor.yaml` `ServiceMonitor` (selecting on the
Service's `app: demo-app` **and** `release: <release-name>` labels) is what makes Prometheus pick it up — confirm it's
actually being scraped in the Prometheus UI under **Status → Targets**, scrape pool
`serviceMonitor/<namespace>/<release>-demo-app/0`, or query it directly:

```promql
version{job="metrics-demo-app"}
```

**It can take up to ~60s after install/upgrade** for the target to go from "config
generated" to actually `up` — the Operator writes the new scrape config, its
config-reloader sidecar has to pick it up and signal Prometheus, and Prometheus's own
Kubernetes service-discovery loop has to run once more. Config appearing under
**Status → Targets** but the target itself missing from
`GET /api/v1/targets` for a minute after `helm upgrade` is this normal propagation
delay, not a broken ServiceMonitor.

To point this at your own app instead: set `demoApp.enabled=false` and add your own
Deployment/Service/`ServiceMonitor` (copy `templates/demo-app-*.yaml` as a starting
point) — `values.yaml` already sets `serviceMonitorSelectorNilUsesHelmValues: false`,
so Prometheus picks up `ServiceMonitor` objects from **any** namespace, not just this
release's own.

### A real bug this chart shipped with, found once `log-stack`/`trace-stack` existed

The demo app's `Deployment`/`Service`/`ServiceMonitor` originally selected on
`app: demo-app` alone. That's fine in isolation — but [`log-stack`](../log-stack/) and
[`trace-stack`](../trace-stack/) each ship their own demo app with that exact same
`app: demo-app` label, no other distinguishing label. The moment more than one of
these releases shares a namespace (verified live: all three installed into `default`
on this cluster), `kubectl get endpointslices` showed this chart's own
`metric-stack-demo-app` Service serving traffic from **`log-stack`'s** pod too —
silently, no error anywhere, because Kubernetes Service selection is pure label
matching with zero concept of "which Helm release created this."

Fixed by adding `release: {{ .Release.Name }}` to the Deployment/Service/ServiceMonitor
labels and selectors — every selector in this chart now requires both `app: demo-app`
and the release name, so it's unambiguous regardless of what else is installed
alongside it. **Changing `spec.selector` on an already-applied Deployment is rejected
by the API server as an immutable field** — upgrading a release installed before this
fix requires deleting the old Deployment object first
(`kubectl delete deployment <release>-demo-app -n <ns>`) so `helm upgrade` can recreate
it fresh; a plain `helm upgrade` on top of the old one fails with
`spec.selector: Invalid value: ...: field is immutable`.

## Uninstall

```bash
helm uninstall metrics -n metrics
kubectl delete namespace metrics   # helm uninstall does not remove a --create-namespace'd namespace

# CRDs are NOT removed by `helm uninstall` (by design, to avoid deleting resources
# that depend on them) — only delete these if nothing else on the cluster uses
# kube-prometheus-stack:
kubectl get crd -o name | grep monitoring.coreos.com | xargs kubectl delete
```
