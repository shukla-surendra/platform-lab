# Elasticsearch (ELK / EFK Stack)

**Category:** observability / monitoring (logs), search

## What it is

A distributed, full-text-search and document-store engine, built on Apache Lucene. In an
observability context it's the storage/query layer for logs — the opposite architectural
choice from [Loki](../loki/README.md): Elasticsearch indexes the **full content** of every
log field, not just labels, which is what makes arbitrary ad hoc search possible but also
what makes it expensive to run at volume.

"ELK" (Elasticsearch, **L**ogstash, **K**ibana) is the classic name for the stack. On
Kubernetes it's usually **EFK** instead — Logstash's heavier JVM footprint gets swapped for
**Fluentd** or **Fluent Bit** as the log shipper, same Elasticsearch + Kibana backend
either way.

## What it's used for on EKS

- **Fluent Bit** (or Fluentd) ships container logs off each node — same DaemonSet pattern
  as Loki's shipping agents, just pointed at Elasticsearch instead.
- **Elasticsearch** stores and indexes the logs, queried with the Query DSL / KQL.
- **Kibana** is the visualization/search UI — Elasticsearch's own equivalent of
  [Grafana](../grafana/README.md), but Elastic-ecosystem-only (logs, and Elastic APM
  traces).
- **Durability**: no object-storage tier by default. Durability comes from
  **replica shards written to EBS-backed PersistentVolumes** on each data node (run as a
  StatefulSet) — lose enough replicas/PVCs at once and you lose data, the same failure mode
  as any stateful database. Index Lifecycle Management (ILM) plus a snapshot repository
  *can* target S3 for backups/archival of older indices, but that's an opt-in policy you
  configure, not automatic the way Loki's S3-native design is.

## When to reach for this over Loki

Full-text/ad hoc search across log content — security investigations, compliance audit
trails, "find every request where field X contained Y" — genuinely needs Elasticsearch's
indexing; label-based filtering (Loki) can't do it. The trade-off is real operational
weight: cluster sizing, shard management, and JVM tuning are ongoing work Loki doesn't
require. See
[`observability-on-eks.md`](../../observability-on-eks.md#logs-the-fork-in-the-road--loki-vs-elkefk)
for the full side-by-side comparison table.

## Alternatives / managed options

- **Amazon OpenSearch Service** — AWS-managed fork of Elasticsearch; same full-text logs
  use case, AWS operates the cluster.
- **Loki** — the cheaper, label-only-indexed alternative when full-text search isn't a hard
  requirement.
- **Splunk** — commercial, full-text log platform with a longer enterprise/SIEM track
  record; see [Splunk](../splunk/README.md).

## Related

- [`observability-on-eks.md`](../../observability-on-eks.md) — full integration-flow
  diagram, the Loki-vs-ELK/EFK comparison table, and the CloudWatch comparison.
- [Loki](../loki/README.md) — the architectural alternative for logs.
- [Grafana](../grafana/README.md) — the visualization-layer alternative to Kibana.
