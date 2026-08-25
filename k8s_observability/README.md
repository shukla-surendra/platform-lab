# k8s_observability

Three independent Helm charts, one per observability signal, all on this repo's
`minikube` cluster — each follows the same shape: **a demo app that actually produces
that signal, a collector/storage backend, and Grafana querying it.** No chart mixes
signals; that split is deliberate (see "Why one signal per chart" below).

| Chart | Signal | Demo app | Backend | Grafana datasource |
|---|---|---|---|---|
| [`metrics-stack/`](metrics-stack/) | Metrics | `prometheus-example-app` (exposes `/metrics`) | Prometheus (`kube-prometheus-stack`) | Prometheus |
| [`log-stack/`](log-stack/) | Logs | busybox loop writing JSON to stdout | Loki + Promtail (`loki-stack`) | Loki |
| [`trace-stack/`](trace-stack/) | Traces | `xk6-client-tracing` (synthetic OTLP spans) | Tempo | Tempo |

Each chart's own README has the full install/upgrade/access/uninstall walkthrough,
with commands verified against a real install on this cluster — this file is the map
between them, not a substitute for reading one directly.

## Quickstart (all three)

```bash
# Metrics
cd metrics-stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm dependency build . && helm install metrics . -n metrics --create-namespace

# Logs
cd ../log-stack
helm repo add grafana https://grafana.github.io/helm-charts
helm dependency build . && helm install log-stack . -n log-stack --create-namespace

# Traces
cd ../trace-stack
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm dependency build . && helm install trace-stack . -n trace-stack --create-namespace
```

Each chart's own README documents the exact release name / namespace this repo's
actual verified install used — which, for all three, ended up being `default` rather
than a dedicated namespace (see the "cross-release label collision" note below for why
that specific choice mattered).

## Why one signal per chart, not one combined chart

[`k8s_explorer/rust-api-observability-stack/`](../k8s_explorer/rust-api-observability-stack/)
already shows the alternative: one chart bundling `kube-prometheus-stack` **and**
`loki-stack` **and** an app, for when metrics+logs+app genuinely need to ship as one
release. Its `values.yaml` is the honest accounting of what that costs — reconciling
two subcharts that each want to own Grafana (`loki-stack.grafana.enabled: false`,
`isDefault: false`, a pinned datasource UID, `serviceMonitorSelectorNilUsesHelmValues`
so the *other* subchart's ServiceMonitors aren't ignored). None of the three charts
here need any of that, because each owns exactly one Grafana pointed at exactly one
backend. The tradeoff is the opposite one: three separate `helm install`s and three
separate Grafanas instead of one — worth it here because the point was learning each
signal's pipeline in isolation, not minimizing release count.

[`k8s_explorer/grafana-log-viewer/`](../k8s_explorer/grafana-log-viewer/) is the
same idea `log-stack/` follows, written earlier and independently — both wrap
`loki-stack`, both hit the same Promtail→Loki URL gotcha (see `log-stack/README.md`),
kept as two separate charts rather than merged since they serve different demo
purposes (that one's `sample-nginx`, this one's own log-generating busybox pod).

## A real cross-chart bug, found by running all three together

Each demo app was originally labeled just `app: demo-app` — fine for any one chart
alone, but all three charts happened to pick the *exact same* label. Installing all
three into the same namespace (`default`, on this cluster's actual verified install)
made that collide for real: `kubectl get endpointslices` showed `metrics-stack`'s own
demo-app **Service** silently serving traffic from `log-stack`'s pod too — pure label
matching, no concept of "which Helm release owns this" anywhere in Kubernetes' object
model. Fixed by adding `release: {{ .Release.Name }}` to every demo app's
Deployment/Service/ServiceMonitor selector, in all three charts — see
[`metrics-stack/README.md`](metrics-stack/README.md#a-real-bug-this-chart-shipped-with-found-once-log-stacktrace-stack-existed)
for the full writeup, including why fixing it required deleting the old Deployment
objects first (`spec.selector` is immutable — `helm upgrade` alone rejects the change).
Worth knowing before copying any of these `templates/demo-app-*.yaml` files as a
starting point for a fourth chart in the same namespace.

## Chart provenance note (as of this writing)

`grafana.github.io/helm-charts`' own `tempo` and `grafana` charts are deprecated —
migrated to `grafana-community/helm-charts` with a stated 2026-01-30 cutoff, already
past by the time `trace-stack` was written, so it pulls both from the new host
instead. `metrics-stack`'s `kube-prometheus-stack` dependency isn't deprecated at all;
`log-stack`'s `loki-stack` dependency *is* deprecated but its replacement on the new
host is a structurally different chart (Loki only, no bundled Promtail/Grafana) — not
a drop-in swap, so `log-stack` stayed on the old (still-functional, verified live)
source rather than taking on that rewrite. See each chart's `Chart.yaml`/README for
specifics.

## A fourth, different kind of project in this directory

[`streaming-drift-detection/`](streaming-drift-detection/) doesn't follow
the one-signal-per-chart split above — it's five *coupled* charts (Kafka →
Feast → Evidently → OTel/Prometheus → Grafana/Alertmanager) forming one
MLOps drift-monitoring pipeline, sharing one namespace instead of one each.
See [`streaming-drift-detection/README.md`](streaming-drift-detection/README.md#why-one-shared-namespace-not-five)
for why that's the right call there and not here. Scaffolded, not yet
installed.

## Related

- [`mlops_aiops/docs/tools/prometheus/README.md`](../mlops_aiops/docs/tools/prometheus/README.md),
  [`.../grafana/README.md`](../mlops_aiops/docs/tools/grafana/README.md),
  [`.../loki/README.md`](../mlops_aiops/docs/tools/loki/README.md),
  [`.../tempo/README.md`](../mlops_aiops/docs/tools/tempo/README.md),
  [`.../cadvisor/README.md`](../mlops_aiops/docs/tools/cadvisor/README.md),
  [`.../kube-state-metrics/README.md`](../mlops_aiops/docs/tools/kube-state-metrics/README.md) —
  what each tool is, how it's normally deployed, and how it compares to alternatives.
- [`k8s_explorer/grafana-log-viewer/`](../k8s_explorer/grafana-log-viewer/) — an earlier,
  independent Loki+Grafana chart (see above).
- [`k8s_explorer/rust-api-observability-stack/`](../k8s_explorer/rust-api-observability-stack/) —
  the one-chart-does-everything alternative these three charts deliberately don't follow.
- [`k8s_explorer/docs/helm-tutorial.md`](../k8s_explorer/docs/helm-tutorial.md) — every
  core Helm command (`install`/`upgrade`/`rollback`/`uninstall`/dependency management)
  explained against a minimal example chart, if any of the commands above are unfamiliar.
