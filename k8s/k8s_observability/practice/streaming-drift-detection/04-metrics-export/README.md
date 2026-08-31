# 04-metrics-export

An [OpenTelemetry](../../mlops_aiops/docs/tools/opentelemetry/README.md)
Collector that receives drift metrics over OTLP from `03-drift-engine`, and
a standalone [Prometheus](../../mlops_aiops/docs/tools/prometheus/README.md)
that scrapes them back out in Prometheus format. Stage 4 of
[`../`](../): the bridge between "a Python process computed a number" and
"that number is a time series Grafana can query."

**Status: scaffolded, not installed.** Both dependency versions
(`opentelemetry-collector` 0.170.0, `prometheus` 29.27.0) were confirmed
live against each chart's own `Chart.yaml` on GitHub; the values below have
not been diffed against either chart's actual schema yet.

## Why the standalone `prometheus` chart, not `kube-prometheus-stack`

[`../../metrics-stack/`](../../metrics-stack/) already wraps
`kube-prometheus-stack` for cluster/workload metrics — but that chart
bundles Alertmanager and Grafana in with Prometheus, and the 5-stage spec
this project follows puts Alertmanager and Grafana in stage 5, not stage 4.
Rather than fight `kube-prometheus-stack`'s bundling (disable two of three
things it installs, the way `metrics-stack/values.yaml` already disables
Alertmanager), this chart uses the plain `prometheus` chart instead — just a
server, nothing else — and `05-dashboards-alerts` brings its own standalone
Alertmanager and Grafana charts. The cost: no `ServiceMonitor`/`PodMonitor`
CRDs (those come from the operator half of `kube-prometheus-stack`, not
plain `prometheus`), so the OTel Collector is scraped via a static
`extraScrapeConfigs` target instead — fine here since there's exactly one
thing to scrape.

## Collector pipeline

`config.receivers.otlp` (gRPC :4317, HTTP :4318) → `config.exporters.prometheus`
(:8889, scraped by the Prometheus server below). No traces/logs pipeline —
this project only ever sends metrics, so those are explicitly nulled out
rather than left as unused default pipelines.

## Fixed Service names

Both subcharts get `fullnameOverride` (`otel-collector`, `prometheus` →
server Service `prometheus-server`, by that chart's `-server` suffix
convention) instead of the default release-name-prefixed names. `03-drift-engine`
and `05-dashboards-alerts` both need to address these by name, and pinning
them here means neither has to guess what release name this chart happened
to be installed under.

## Install

```bash
helm dependency build .
helm install metrics-export . -n drift-detection --create-namespace
```

## Related

- [`../README.md`](../README.md) — the full pipeline and data flow diagram.
- [`../../metrics-stack/`](../../metrics-stack/) — the `kube-prometheus-stack`
  wrapper this chart deliberately doesn't reuse (own cluster, own Prometheus
  — see `../README.md#why-this-doesnt-reuse-metrics-stacks-prometheusgrafana`).
- [`../../mlops_aiops/docs/tools/opentelemetry/README.md`](../../mlops_aiops/docs/tools/opentelemetry/README.md),
  [`.../prometheus/README.md`](../../mlops_aiops/docs/tools/prometheus/README.md).
