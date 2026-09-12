# LGTM Stack

**Category:** observability / monitoring (open-source stack, unified metrics+logs+traces)

## What it is

Grafana Labs' name for their own opinionated, fully open-source observability stack:

| Letter | Component | Signal |
|---|---|---|
| **L** | [Loki](../loki/README.md) | Logs |
| **G** | [Grafana](../grafana/README.md) | Visualization / dashboards / alerting (the shared UI on top of the other three) |
| **T** | [Tempo](../tempo/README.md) | Traces |
| **M** | [Mimir](../mimir/README.md) | Metrics (long-term, Prometheus-compatible storage) |

Verified directly from Grafana Labs: Loki, Grafana, and Tempo existed first; the acronym
was completed in **March 2022** when Mimir shipped, rounding out L-G-T into L-G-T-**M**.
The name is deliberate wordplay — it reads as the common code-review phrase "looks good to
me," doubling as a claim about what you get once metrics, logs, and traces are unified in
one place.

## Why one Grafana UI instead of four separate tools

Each backend is single-purpose and independently swappable, but they're designed to be
run together and queried from a single [Grafana](../grafana/README.md) instance: you
build one dashboard that queries Mimir for a latency graph, click through to Loki for the
logs from that same time window, and pivot to Tempo for the exact trace of a slow
request — one UI, one query experience (PromQL for Mimir, LogQL for Loki, TraceQL for
Tempo), instead of separate tools with separate logins per signal.

## Where Prometheus fits — and where it doesn't

**Prometheus is not one of the four LGTM letters.** This is a common point of confusion
(including in earlier docs in this project, since corrected) because Mimir is
purpose-built to be a Prometheus-compatible long-term backend: it accepts Prometheus's
own `remote_write` protocol and answers queries in PromQL, so a Prometheus server
scraping metrics locally and forwarding them to Mimir for durable storage is the *typical*
deployment shape — but Prometheus itself is a separate, optional piece you put in front
of Mimir, not the "M". Plenty of LGTM deployments skip a standalone Prometheus server
entirely and feed Mimir directly via [OpenTelemetry](../opentelemetry/README.md) or
Grafana Alloy instead.

## How data gets in: Grafana Alloy / OpenTelemetry

None of the four backends collect telemetry themselves — something has to ship data into
them. Grafana Labs' current recommended agent is **Grafana Alloy** (successor to Promtail
for logs and the Grafana Agent generally), which is OpenTelemetry-Collector-compatible and
can receive OTLP and route it to Loki, Mimir, and Tempo simultaneously — see
[OpenTelemetry](../opentelemetry/README.md) for the underlying standard this is built on.

## Deployment options

- **Self-managed** — run each of the four components yourself (Helm charts, e.g.
  `loki-stack`/`kube-prometheus-stack` for the metrics side, standalone charts for Tempo
  and Mimir).
- **Grafana Cloud** — Grafana Labs' fully managed hosted version of the same stack.
- **Grafana Enterprise Stack** — self-hosted, but with Grafana Labs' commercial support
  and enterprise features layered on top of the open-source core.

## Licensing

Loki, Tempo, and Mimir are all released under **AGPLv3**. This matters operationally if
you're considering redistributing or offering these as a hosted service yourself — AGPLv3
is a stronger copyleft license than the Apache 2.0 used by, e.g., Prometheus or
OpenTelemetry.

## Alternatives

| Tool | Angle |
|---|---|
| **[SigNoz](../signoz/README.md)** | Single unified database ([ClickHouse](../clickhouse/README.md)) for all three signals, instead of one specialized backend per signal — architecturally the opposite bet from LGTM's per-signal-optimized design |
| **[Datadog](../datadog/README.md) / [New Relic](../new-relic/README.md)** | Commercial, fully managed, no self-hosting — same trade-off SigNoz avoids while staying open-source, that LGTM also avoids by staying self-hostable |
| **[Elasticsearch](../elasticsearch/README.md) (ELK/EFK)** | Full-text log search specifically, predates LGTM as a logging-first architecture rather than a unified metrics+logs+traces stack |

## Related

- [Loki](../loki/README.md), [Grafana](../grafana/README.md), [Tempo](../tempo/README.md),
  [Mimir](../mimir/README.md) — the four components, each documented in full on their own
  pages.
- [SigNoz](../signoz/README.md) — the clearest architectural counterpoint: one database
  for all signals instead of four specialized backends.
- [OpenTelemetry](../opentelemetry/README.md) — the instrumentation standard feeding this
  stack via Grafana Alloy or a standard OTel Collector.
- [`observability-on-eks.md`](../../observability-on-eks.md) and
  [`observability-terminology.md`](../../observability-terminology.md) — the broader
  observability landscape this stack sits within.
