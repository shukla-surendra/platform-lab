# New Relic

**Category:** observability / monitoring (commercial, all-in-one)

## What it is

A commercial, SaaS, all-in-one observability platform — one of the original dedicated APM
(Application Performance Monitoring) vendors, now covering metrics, logs, distributed
tracing, and an AI-assisted analysis layer on top, similar in overall positioning to
[Datadog](../datadog/README.md).

## What it's used for

- **APM as the historical core strength** — deep application-level performance tracing
  (which function/DB query/external call is slow) is where New Relic's product line
  originated, before expanding into full-stack observability.
- Accepts [OpenTelemetry](../opentelemetry/README.md) data directly, same as Datadog and
  AWS X-Ray, so OTel-instrumented applications aren't locked into any one backend.
- Same all-in-one convenience trade-off as Datadog: comparatively little setup versus
  assembling an open-source stack, at commercial SaaS cost and vendor lock-in.

## Alternatives

- **Datadog** — very similar positioning; see [Datadog](../datadog/README.md). The choice
  between the two is usually driven by existing vendor relationships, pricing negotiation,
  or specific feature depth (e.g. security monitoring) rather than a fundamental
  architectural difference.
- **Dynatrace** — same all-in-one category, with a causal-AI (Davis AI) root-cause engine
  as its main differentiator; see [Dynatrace](../dynatrace/README.md).
- **Splunk** — stronger SIEM/security-log roots; see [Splunk](../splunk/README.md).
- **Self-hosted**: Prometheus + Grafana + Loki/Elasticsearch + Tempo/Jaeger.

## Related

- [`observability-on-eks.md`](../../observability-on-eks.md) — where commercial
  all-in-one platforms fit relative to self-hosted and AWS-native paths.
