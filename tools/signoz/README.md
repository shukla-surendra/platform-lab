# SigNoz

**Category:** observability / monitoring (open-source, unified metrics+logs+traces)

## What it is

Open-source, self-hosted observability platform unifying metrics, logs, and traces —
positioned as an open-source alternative to [Datadog](../datadog/README.md)/
[New Relic](../new-relic/README.md), but architecturally different from the
[LGTM stack](../lgtm-stack/README.md) (Loki/Grafana/Tempo/Mimir) approach too. Where LGTM
uses one specialized store per signal (Mimir for metrics, Loki for logs, Tempo for
traces), **SigNoz uses a single database — [ClickHouse](../clickhouse/README.md) — for
all three signals.**
Founded by Pranay Prateek and Ankit Nayan, went through Y Combinator (W21). Core code is
MIT-licensed; a separate `ee/` (enterprise) directory carries a proprietary license.

## Why one database for three signals, instead of three specialized ones

The LGTM approach exists because each signal type has different access patterns — Loki's
label-only indexing is optimized specifically for logs, Tempo's design is trace-specific.
SigNoz's bet is that [ClickHouse](../clickhouse/README.md)'s columnar storage is fast
enough at the aggregate-query patterns all three signals actually need (group-by-service,
filter-by-time-range, percentile calculations) that one well-chosen general-purpose OLAP
engine can serve all three without needing purpose-built stores per signal — trading some
of Loki/Tempo's signal-specific optimization for a simpler operational footprint (one
database to run and scale, not three).

## What it's used for

- **Built OpenTelemetry-native from day one** — verified directly from SigNoz's own docs,
  not a bolt-on the way some older platforms added OTel support after the fact.
- Ships its own distribution of the **OpenTelemetry Collector**, pre-configured to accept
  OTLP, Jaeger, Zipkin, Kafka, and OpenCensus input, translate protocols as needed, and
  write directly into ClickHouse — see [OpenTelemetry](../opentelemetry/README.md) for the
  underlying standard this distribution is built on.
- Dashboards, alerting, and trace/log/metric correlation in one UI — the SigNoz-native
  equivalent of what [Grafana](../grafana/README.md) provides on top of separate backends.

## Alternatives

| Tool | Angle |
|---|---|
| **[LGTM stack](../lgtm-stack/README.md)** (Loki+Grafana+Tempo+Mimir) | Specialized store per signal, more mature/battle-tested individually, more moving parts operationally |
| **[Datadog](../datadog/README.md) / [New Relic](../new-relic/README.md)** | Commercial, fully managed, no self-hosting at all — the trade-off SigNoz exists specifically to avoid while staying open-source |
| **[Elasticsearch](../elasticsearch/README.md) (ELK/EFK)** | Full-text log search specifically; not a unified metrics+logs+traces platform the way SigNoz is |

## Related

- [ClickHouse](../clickhouse/README.md) — the storage engine underneath every SigNoz
  signal.
- [OpenTelemetry](../opentelemetry/README.md) — the instrumentation standard SigNoz's
  Collector distribution is built on.
- [`observability-on-eks.md`](../../observability-on-eks.md) and
  [`observability-terminology.md`](../../observability-terminology.md) — the broader
  observability landscape SigNoz sits within.
