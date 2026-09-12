# Grafana

**Category:** observability / monitoring (Kubernetes/EKS)

## What it is

Visualization/dashboarding layer only — it stores no data itself. You
point it at data sources and build dashboards/alerts on top of whatever
they return.

## What it's used for on EKS

Queries [Prometheus](../prometheus/README.md) for metrics and
[Loki](../loki/README.md) for logs (and often [Tempo](../tempo/README.md) for traces),
giving one UI across metrics + logs + traces for an EKS cluster instead of separate tools
per signal type.

## Deployment

Comes bundled in the **`kube-prometheus-stack`** Helm chart alongside
Prometheus, Alertmanager, node-exporter, and kube-state-metrics — so a
single Helm install typically gets you Grafana pre-wired to Prometheus.
Loki is usually added as a second data source afterward.

## Alternatives / managed options

- **Amazon Managed Grafana (AMG)** — AWS-managed Grafana; can point at
  Amazon Managed Service for Prometheus (AMP) and/or CloudWatch, so you're
  not operating the Grafana server yourself.
- **[CloudWatch](../cloudwatch/README.md) dashboards / Container Insights** —
  AWS-native alternative if you want to avoid running a separate
  visualization layer entirely, at the cost of flexibility/portability
  compared to Grafana.

## Related

Part of the metrics/logs/visualization trio commonly run together on EKS
— see [LGTM stack](../lgtm-stack/README.md) for the full stack this name
refers to (Loki, Grafana, Tempo, [Mimir](../mimir/README.md)), or
[`docs/observability-on-eks.md`](../../observability-on-eks.md) for the
full landscape with an integration-flow diagram, including how Kibana
compares as the alternative visualization layer if logs go through
[Elasticsearch](../elasticsearch/README.md) instead of Loki.
