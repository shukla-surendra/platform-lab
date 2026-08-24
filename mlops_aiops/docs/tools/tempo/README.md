# Tempo

**Category:** observability / monitoring (tracing)

## What it is

Grafana Labs' distributed tracing backend — stores and queries traces received from an
[OpenTelemetry](../opentelemetry/README.md) Collector (or Jaeger/Zipkin protocols
directly). Pairs naturally with [Grafana](../grafana/README.md) — same team, same UI as
[Prometheus](../prometheus/README.md)/[Mimir](../mimir/README.md) (metrics) and
[Loki](../loki/README.md) (logs), which is exactly what the
[LGTM stack](../lgtm-stack/README.md) (Loki, Grafana, Tempo, Mimir) refers to.

## What it's used for on EKS

Receives spans from an OTel Collector running as a Deployment or sidecar, stores them, and
serves trace-lookup queries from Grafana — typically "jump from a slow request in a
dashboard straight to its full trace" as the actual workflow this enables.

**Durability**: like Loki, Tempo is designed around **S3/object storage** as its trace
block store from the start — not an afterthought, the same design philosophy Loki uses for
logs. Locally, that's typically [MinIO](../minio/README.md) standing in for S3.

## Deployment and usage — verified live against this repo's cluster

Deployed via [`k8s_observability/trace-stack/`](../../../../k8s_observability/trace-stack/)
(the `grafana-community/tempo` chart, single-binary mode — the older `grafana/tempo`
chart at `grafana.github.io/helm-charts` is deprecated, migrated to
`grafana-community/helm-charts`). Two separate ports matter and are easy to confuse:
`:3200` is Tempo's own HTTP query API (what Grafana's Tempo datasource points at);
`:4317`/`:4318` are the OTLP gRPC/HTTP receivers (what anything *sending* traces points
at) — enabled by default in this chart, nothing to turn on.

Traces don't exist for free the way logs (any pod's stdout, tailed by Promtail with zero
app changes) or basic metrics (cAdvisor/kube-state-metrics, scraped with zero app
changes) do — something has to actually emit OTLP spans. `trace-stack`'s demo app is
`ghcr.io/grafana/xk6-client-tracing`, a k6-based synthetic trace generator the Tempo
project's own docs use for exactly this. It bundles a script
(`/example-script.js`) that fabricates a realistic multi-service trace —
`shop-backend → auth-service → article-service → postgres`, plus a `cart-service` flow
— and sends it over OTLP/gRPC on a loop, reading the target from an `ENDPOINT` env var
(`__ENV.ENDPOINT || "otel-collector:4317"`, verified by reading the script directly
inside a running container). No app instrumentation to write, no OTel SDK to configure
— just point `ENDPOINT` at `<tempo-release>:4317` and real, queryable, multi-span
traces start landing within seconds:

```bash
curl -s "http://<tempo-svc>:3200/api/search?tags=service.name%3Dshop-backend&limit=3"
curl -s "http://<tempo-svc>:3200/api/traces/<traceID>"
```

## Alternatives

- **Jaeger** — older, CNCF-graduated, still widely used, has its own dedicated UI rather
  than living inside Grafana; see [Jaeger](../jaeger/README.md).
- **Vendor-hosted tracing** (Datadog APM, New Relic distributed tracing) — no self-hosted
  backend to run at all, at commercial SaaS cost.

## Related

- [OpenTelemetry](../opentelemetry/README.md) — the instrumentation/collection layer
  feeding Tempo.
- [Grafana](../grafana/README.md), [Prometheus](../prometheus/README.md),
  [Loki](../loki/README.md), [Mimir](../mimir/README.md) — the rest of the
  [LGTM stack](../lgtm-stack/README.md).
- [`observability-on-eks.md`](../../observability-on-eks.md) — full integration-flow
  diagram.
