# Loki

**Category:** observability / monitoring (Kubernetes/EKS)

## What it is

Log aggregation system — described as "[Prometheus](../prometheus/README.md)
but for logs." It only indexes **labels** (e.g. namespace, pod, container)
rather than full-text content, which keeps storage/indexing costs much
lower than full-text log systems (e.g. [Elasticsearch](../elasticsearch/README.md)/
OpenSearch). Queried with **LogQL**.

## What it's used for on EKS

Loki itself only stores and serves logs — it doesn't collect them. On EKS
you need a **shipping agent** running as a DaemonSet on every node to tail
container logs and push them to Loki:

- **Promtail** — Loki's original/traditional shipping agent.
- **Grafana Alloy** — Promtail's successor, the currently recommended agent.
- **Fluent Bit** — a more general-purpose log shipper, also commonly used
  to ship to Loki.

## Deployment

Usually installed via the `loki-stack` Helm chart, or `loki` + a shipping
agent (`promtail`/`alloy`) as separate charts. Wired into the same
[Grafana](../grafana/README.md) instance that's already querying
[Prometheus](../prometheus/README.md) (e.g. from `kube-prometheus-stack`),
as a second data source — giving one UI for both metrics and logs. Loki, too, stores
chunks in S3-compatible object storage — [MinIO](../minio/README.md) is the common
self-hosted stand-in for local/CI setups.

## Usage — verified live against this repo's cluster

Deployed via [`k8s/k8s_observability/practice/log-stack/`](../../../../k8s/k8s_observability/practice/log-stack/)
(the `loki-stack` chart — Loki + Promtail + a standalone Grafana, own Grafana
instance rather than sharing `kube-prometheus-stack`'s, see that chart's README for
why). Two things confirmed live, both silent failure modes if wrong: the Loki
datasource UID must be pinned in `values.yaml` (`loki.datasource.uid`) or dashboards
referencing a fixed uid render empty with no error; and Promtail's
`pipelineStages` must match the cluster's actual container runtime
(`docker: {}` vs `cri: {}`) or `| json` LogQL parsing silently parses the runtime's
stdout wrapper instead of the log line, so every `level`-filtered query reads zero
with logs still visibly arriving in the raw stream.

## Related

Part of the metrics/logs/visualization trio commonly run together on EKS:
Prometheus (metrics), Loki (logs), Grafana (visualization) — see the
[LGTM stack](../lgtm-stack/README.md) for the full stack this is part of.
For a direct comparison against the alternative logging architecture
([Elasticsearch](../elasticsearch/README.md)/ELK/EFK) and a full
integration-flow diagram, see
[`docs/observability-on-eks.md`](../../observability-on-eks.md).
