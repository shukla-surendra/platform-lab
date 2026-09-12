# Prometheus

**Category:** observability / monitoring (Kubernetes/EKS)

## What it is

Time-series metrics database. It periodically *scrapes* HTTP `/metrics`
endpoints, stores the resulting numeric time series, lets you query them
with **PromQL**, and can fire alerts on thresholds via a companion
component, **Alertmanager**.

## What it's used for on EKS

- Your own pods need to expose a `/metrics` endpoint for Prometheus to
  scrape application-level metrics.
- **node-exporter** — a DaemonSet that exposes node-level metrics (CPU,
  memory, disk) per EKS node.
- **kube-state-metrics** — exposes Kubernetes object state (pod/deployment/
  replica counts, status, restarts) as metrics.
- Prometheus scrapes all three (your app, node-exporter, kube-state-metrics)
  to get full cluster + workload visibility.

## Deployment

Most commonly installed via the **`kube-prometheus-stack`** Helm chart,
which bundles Prometheus + Alertmanager + [Grafana](../grafana/README.md) +
node-exporter + kube-state-metrics in one install — the standard starting
point for EKS observability.

## Alternatives / managed options

- **Amazon Managed Service for Prometheus (AMP)** — AWS-managed, Prometheus
  API-compatible metrics store. You still run a scraper agent on EKS (e.g.
  the ADOT collector) to ship metrics into it; you're not running/operating
  the Prometheus server yourself.
- **[CloudWatch](../cloudwatch/README.md) Container Insights** — AWS-native
  metrics (and logs) for EKS in one product, no extra stack to run, but
  less flexible/portable than self-hosting Prometheus and query semantics
  differ from PromQL.

## Related

Prometheus, [Loki](../loki/README.md), and [Grafana](../grafana/README.md)
are commonly deployed together on EKS as the metrics/logs/visualization
trio. Grafana Labs' [LGTM stack](../lgtm-stack/README.md) (plus
[Tempo](../tempo/README.md) for traces and [Mimir](../mimir/README.md) as the
scalable, Prometheus-`remote_write`-compatible long-term backend) covers metrics,
logs, and traces in one Grafana UI. See
[`docs/observability-on-eks.md`](../../observability-on-eks.md) for the
full landscape (including ELK/EFK, tracing, and alerting) with an
integration-flow diagram.
