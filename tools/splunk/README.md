# Splunk

**Category:** observability / monitoring (commercial, logs/SIEM roots)

## What it is

A commercial platform with the longest enterprise track record in this list — originally
built around full-text log search and indexing (its Search Processing Language, SPL, is
the closest analog to what [Elasticsearch](../elasticsearch/README.md)'s Query DSL does),
later extended into full observability (metrics, traces) and, via **Splunk ITSI** (IT
Service Intelligence), into AIOps-style event correlation and anomaly detection.

## What it's used for

- **Security and compliance log analysis (SIEM)** is Splunk's deepest historical strength
  — many enterprises that already run Splunk for security/audit logging extend it to
  general observability rather than adopting a second tool.
- **Splunk ITSI** is one of the named AIOps platforms referenced in
  [`mlops-aiops-llmops.md`](../../mlops-aiops-llmops.md#aiops) — it sits on top of ingested
  telemetry (which can come from Splunk's own log ingestion or from metrics/traces) and
  does the event-correlation/anomaly-detection work AIOps platforms are defined by.
- General observability (metrics, APM) has been added over time, competing more directly
  with [Datadog](../datadog/README.md)/[New Relic](../new-relic/README.md) in that
  capacity, though SIEM/security remains its most distinctive strength.

## Alternatives

- **Elasticsearch/OpenSearch** — open-source alternative for the full-text log/search use
  case specifically, without the SIEM-specific tooling.
- **Datadog / New Relic / Dynatrace** — closer competitors for the general
  observability/APM use case, without Splunk's security/SIEM depth. See
  [Datadog](../datadog/README.md), [New Relic](../new-relic/README.md),
  [Dynatrace](../dynatrace/README.md).

## Related

- [Elasticsearch](../elasticsearch/README.md) — the open-source analog for the full-text
  log/search half of what Splunk does.
- [`mlops-aiops-llmops.md`](../../mlops-aiops-llmops.md#aiops) — Splunk ITSI in the AIOps
  discipline context, including Gartner's definition and the analyst-firm disagreement on
  what "AIOps platform" even means.
