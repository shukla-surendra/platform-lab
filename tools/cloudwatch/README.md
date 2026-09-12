# Amazon CloudWatch

**Category:** observability / monitoring (metrics, logs, tracing, alerting — AWS-native)

## What it is

AWS's own, fully-managed observability suite — metrics, logs, alarms, and (via X-Ray)
tracing, with **AWS owning the storage durability question entirely.** No PVC to size, no
S3 bucket to wire up, no ILM policy to configure — the trade-off for that convenience is
AWS's own query languages and pricing model instead of PromQL/LogQL/Query-DSL, and
AWS-only portability.

## What it's used for on EKS

- **CloudWatch Container Insights** (or the newer **CloudWatch Observability EKS
  add-on**) runs a CloudWatch agent + Fluent Bit as DaemonSets, auto-collecting node/pod/
  container metrics and logs with almost no configuration.
- **CloudWatch Logs** — each pod's stdout/stderr lands in a log group, queried with
  **CloudWatch Logs Insights** — a purpose-built filter/stats query language, not
  full-text search like [Elasticsearch](../elasticsearch/README.md), not label-first like
  LogQL.
- **CloudWatch Metrics** — push-based (agents push to the CloudWatch API, unlike
  [Prometheus](../prometheus/README.md)'s pull/scrape model). Default retention is much
  longer out of the box (up to 15 months, at decreasing resolution) with no separate
  long-term-storage component needed.
- **CloudWatch Alarms** — the alerting layer, wired to SNS and from there to
  Slack/PagerDuty/Lambda/email — roughly the equivalent of Alertmanager or Grafana
  Alerting.
- **AWS X-Ray** — the traces equivalent if staying fully AWS-native instead of
  [OpenTelemetry](../opentelemetry/README.md) + Tempo/Jaeger; X-Ray now also accepts OTLP
  directly.

## Alternatives / when to use what instead

See [`observability-on-eks.md`](../../observability-on-eks.md#cloudwatch-vs-the-self-hosted-stack)
for the full comparison table against Prometheus+Grafana, Loki, and Elasticsearch across
setup effort, storage durability, query language, retention, cost model, and portability.
Short version: CloudWatch is the lowest-setup, least-portable option; the self-hosted stack
trades setup effort for portability and query power. They're not mutually exclusive — a
common pattern is CloudWatch as the always-on zero-maintenance baseline, with
Prometheus+Grafana layered on top for dashboards and alerting flexibility.

## Related

- [`observability-on-eks.md`](../../observability-on-eks.md) — the dedicated CloudWatch
  comparison section and the AWS-native integration-flow diagram.
- [Prometheus](../prometheus/README.md), [Loki](../loki/README.md),
  [Elasticsearch](../elasticsearch/README.md) — the self-hosted alternatives CloudWatch is
  compared against.
