# Jaeger

**Category:** observability / monitoring (tracing)

## What it is

A distributed tracing backend originally built at Uber, now a graduated CNCF project —
older and more independently-established than [Tempo](../tempo/README.md), with its own
dedicated web UI rather than living inside Grafana. Receives spans via the
[OpenTelemetry](../opentelemetry/README.md) protocol (or its own native Jaeger protocol,
which predates OTel).

## What it's used for on EKS

Same role as Tempo — the storage/query backend a trace-producing pipeline sends spans to,
so a slow request can be traced across every service it touched. Choosing Jaeger over
Tempo is largely a question of whether you want tracing to live in its own dedicated UI
(Jaeger) or unified into the same Grafana instance already serving metrics and logs
(Tempo) — same underlying signal, different visualization philosophy.

## Alternatives

- **Tempo** — if already standardized on Grafana for metrics/logs, keeping traces in the
  same UI is usually the deciding factor; see [Tempo](../tempo/README.md).
- **Zipkin** — an older, simpler tracing backend, largely superseded by Jaeger/Tempo in new
  deployments but still present in some legacy stacks.
- **Vendor-hosted tracing** (Datadog APM, New Relic) — no self-hosted backend at all.

## Related

- [OpenTelemetry](../opentelemetry/README.md) — the instrumentation/collection layer
  feeding Jaeger.
- [`observability-on-eks.md`](../../observability-on-eks.md#traces-the-pillar-people-forget)
  — where tracing fits in the full EKS observability picture.
