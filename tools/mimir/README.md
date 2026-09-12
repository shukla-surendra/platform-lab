# Mimir

**Category:** observability / monitoring (metrics, long-term storage)

## What it is

Grafana Labs' horizontally scalable, highly available, multi-tenant, **long-term storage
backend for [Prometheus](../prometheus/README.md) metrics**. Announced by Grafana Labs in
March 2022. It is not a replacement for Prometheus's scraping model — Prometheus (or an
OTel Collector) still does the actual scraping/collection; Mimir is what you point
Prometheus's `remote_write` at when you need retention, scale, or multi-tenancy beyond
what a single Prometheus server's local TSDB can hold. It speaks Prometheus's own
`remote_write` API and answers queries in **PromQL**, so existing Prometheus dashboards
and alert rules keep working unchanged. Licensed **AGPLv3**. Verified from Grafana Labs'
own GitHub repo and blog.

## Why it exists

A single Prometheus server's local time-series database doesn't horizontally scale or
replicate — it's built for one node holding recent data. Mimir's microservices
architecture splits ingestion, storage, and querying into independently scalable
components, and stores data in **object storage** (S3, GCS, Azure Blob, or any
S3-compatible store) instead of local disk — the same durability model
[Loki](../loki/README.md) and [Tempo](../tempo/README.md) use for logs and traces. Grafana
Labs' own testing describes handling up to 1 billion active time series. For local
dev/test, that object storage is commonly [MinIO](../minio/README.md) rather than real
AWS S3.

## What it's used for

- Long-term, durable retention of Prometheus metrics beyond a single server's local disk.
- Multi-tenant metrics storage — many independent Prometheus-sending sources into one
  Mimir cluster, isolated per tenant.
- The **"M"** in the [LGTM stack](../lgtm-stack/README.md) — the metrics component
  alongside Loki (logs), Grafana (visualization), and Tempo (traces).

## Alternatives

- **Prometheus alone** (no remote-write backend) — simplest, but no long-term retention,
  no HA, no multi-tenancy; fine for smaller/single-cluster setups.
- **Amazon Managed Service for Prometheus (AMP)** — AWS-managed, Prometheus
  API-compatible; see [Prometheus](../prometheus/README.md).
- **Thanos** — the other major open-source project solving the same "long-term,
  scalable Prometheus storage" problem, not covered in depth here yet.

## Related

- [Prometheus](../prometheus/README.md) — the scraper/collector Mimir stores data for.
- [LGTM stack](../lgtm-stack/README.md) — Mimir is the fourth component completing the
  acronym.
- [Loki](../loki/README.md), [Tempo](../tempo/README.md) — the sibling Grafana Labs
  backends for logs and traces, same object-storage design philosophy.
