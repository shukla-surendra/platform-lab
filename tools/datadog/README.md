# Datadog

**Category:** observability / monitoring (commercial, all-in-one)

## What it is

A commercial, SaaS, all-in-one observability platform — metrics, logs, distributed tracing
(APM), and increasingly security monitoring and AIOps-style anomaly detection
("Watchdog"), all under one product and one bill, rather than assembling
Prometheus+Loki+Tempo+Grafana yourself.

## What it's used for

- **Fastest path to full observability** on any infrastructure (Kubernetes, EC2,
  serverless, on-prem) — install the Datadog Agent, and metrics/logs/traces start flowing
  with comparatively little manual wiring versus standing up an open-source stack.
- Accepts [OpenTelemetry](../opentelemetry/README.md) (OTLP) directly, so existing OTel
  instrumentation doesn't need to be redone to send data to Datadog.
- **Datadog Watchdog** — the AIOps-style layer: automated anomaly detection and root-cause
  suggestions on top of the same telemetry, without hand-writing every alerting rule.

## Trade-off vs. the self-hosted stack

Same shape of trade-off as [CloudWatch](../cloudwatch/README.md) vs.
Prometheus+Grafana+Loki: far less setup and operational burden, at the cost of vendor
lock-in and a cost model that scales with data volume/hosts rather than infrastructure you
provision yourself. Commonly the right call when engineering time is scarcer than the
recurring SaaS cost, or when a team doesn't want to own cluster sizing/upgrades for an
observability backend at all.

## Alternatives

- **New Relic** — very similar positioning (all-in-one commercial APM/observability); see
  [New Relic](../new-relic/README.md).
- **Dynatrace** — same all-in-one category, differentiated by Davis AI's deterministic
  causal topology model versus Watchdog's more statistical anomaly detection; see
  [Dynatrace](../dynatrace/README.md).
- **Splunk** — stronger historical roots in log/SIEM use cases specifically; see
  [Splunk](../splunk/README.md).
- **Self-hosted**: Prometheus + Grafana + Loki/Elasticsearch + Tempo/Jaeger — full control
  and portability, at the cost of operating it yourself. See
  [`observability-on-eks.md`](../../observability-on-eks.md) for that comparison in depth.

## Related

- [`observability-on-eks.md`](../../observability-on-eks.md) — where commercial platforms
  fit relative to the self-hosted and AWS-native paths.
- [`mlops-aiops-llmops.md`](../../mlops-aiops-llmops.md) — Datadog Watchdog as an example
  of an AIOps-branded capability layered on observability telemetry.
