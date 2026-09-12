# OpenTelemetry (OTel)

**Category:** observability / monitoring (tracing, increasingly metrics/logs too)

## What it is

A vendor-neutral instrumentation standard — an SDK for adding spans/traces (and
increasingly metrics and logs) to application code, plus a **Collector** that receives
that telemetry and exports it onward to whichever backend you choose. The point of
OpenTelemetry is decoupling *instrumentation* from *backend*: instrument once with the OTel
SDK, and send the data to Tempo, Jaeger, Datadog, New Relic, or several at once, without
re-instrumenting the application if the backend choice changes later.

## What it's used for

- **Metrics tell you *that* p99 latency spiked; logs might tell you an error occurred
  somewhere; only a trace tells you which specific service call in a chain added the
  latency.** This is the pillar most teams add last, after metrics and logs are already in
  place.
- On EKS: instrument application code with the OTel SDK, run an **OTel Collector** (as a
  Deployment or sidecar) to receive spans, and export them to a trace backend — see
  [Tempo](../tempo/README.md) or [Jaeger](../jaeger/README.md).
- A concrete example of a vendor shipping its own OTel Collector distribution:
  [SigNoz](../signoz/README.md) bundles a pre-configured Collector that accepts OTLP (plus
  Jaeger/Zipkin/Kafka/OpenCensus input) and writes straight into
  [ClickHouse](../clickhouse/README.md).
- OTel is also the ingestion format several vendor platforms now accept directly — AWS
  X-Ray, Datadog, and New Relic all accept OTLP (the OpenTelemetry wire protocol), so
  instrumenting with OTel doesn't lock you into an open-source-only backend.

## Alternatives

- **Vendor-specific SDKs** (Datadog's `dd-trace`, New Relic's agents) — less portable
  across backends, but sometimes more turnkey/feature-complete for that specific vendor's
  platform.
- **AWS X-Ray SDK** — AWS-native alternative if staying fully within CloudWatch's
  ecosystem; see [CloudWatch](../cloudwatch/README.md). X-Ray now also accepts OTLP
  directly, so the two aren't strictly either/or.

## Related

- [Tempo](../tempo/README.md) and [Jaeger](../jaeger/README.md) — the two most common
  open-source backends OTel data lands in.
- [SigNoz](../signoz/README.md) — an OTel-native platform with its own Collector
  distribution, backed by [ClickHouse](../clickhouse/README.md).
- [`observability-on-eks.md`](../../observability-on-eks.md#traces-the-pillar-people-forget)
  — full integration-flow diagram including the tracing pipeline.
