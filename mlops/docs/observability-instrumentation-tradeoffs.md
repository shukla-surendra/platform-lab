# Instrumentation Tradeoffs: Who Measures What, and What It Costs

[`observability-on-eks.md`](observability-on-eks.md) covers which tools do what, and
[`observability-terminology.md`](observability-terminology.md) covers what the words mean.
This doc sits between them: given that vocabulary and that toolset, who is actually
responsible for producing telemetry, and what does producing it cost the application that
generates it?

## Two ways telemetry gets produced

1. **External/automatic** — infrastructure agents, Kubernetes, cloud services, service
   meshes, APM agents, database monitoring, reverse proxies, network monitoring. Collected
   *about* the application without the application doing anything.
2. **Application instrumentation** — application/business metrics, application-specific
   traces, structured logs, domain-specific events. Requires the application to emit
   something, because the meaning is domain-specific.

Production systems generally need both, and the dividing line is a single question:

> **If infrastructure can know something without understanding the application's business
> logic, it can usually collect it externally. If understanding the domain is required, the
> application has to expose that information itself.**

| What's observed | Usually collected by | Needs app instrumentation? |
|---|---|---|
| CPU / memory / disk | Kubernetes / cloud / node agent | No |
| Pod/container restarts | Kubernetes | No |
| Network traffic | Platform / service mesh / agent | Often no |
| HTTP request rate / latency | Ingress / service mesh / APM | Sometimes no |
| Queue depth | Queue service | No |
| Application exceptions | Logs / APM | Often automatic |
| DB query latency | DB / APM / instrumentation | Depends |
| Domain-specific outcomes (e.g. "documents processed", "OCR accuracy", "which model served this request") | Application | Yes |

## Responsibility split

| Platform / DevOps / SRE provides | Application developers provide |
|---|---|
| Kubernetes/node/container metrics | Business semantics — what counts as success vs. failure |
| Log collection pipeline | Which operations/events actually matter |
| OTel Collector, storage, retention, sampling config | The instrumentation itself (metrics, traces, structured log fields) |
| Dashboards, alerting infrastructure | What's needed to debug one specific failed request |

The platform team can build a perfect telemetry pipeline and it still won't know that
`documents_failed_total` matters more than `helper_function_calls_total` — that judgment
call belongs to whoever owns the domain logic.

## Automatic vs. manual instrumentation

Automatic instrumentation (framework/library/agent-provided) captures generic boundaries —
HTTP request/response/status/latency, DB calls, RPC calls. It sees:

```
POST /invoice = 2.8 seconds
```

Manual instrumentation exposes the internal stages that only the developer understands are
meaningful:

```
POST /invoice
    |
    +-- download PDF      200ms
    +-- conversion        500ms
    +-- OCR                1.5s
    +-- validation         300ms
```

**Don't instrument every function.** Focus on meaningful boundaries: HTTP requests, queue
messages, external API calls, database operations, important business workflows — not
`foo()`, `bar()`, `calculate_x()`. More useful signal per unit of instrumentation overhead.

## Instrumentation should not sit on the critical path

The measurement itself (`duration = 1.42s`) is cheap. What's potentially expensive is
**exporting** that measurement over the network synchronously.

Bad — export blocks the business operation:

```
Process request → create metric → HTTP call to backend → WAIT → continue
```

Good — record locally, export asynchronously:

```
                 APPLICATION
                      |
             +--------+--------+
             |                 |
       Process request     Telemetry
             |                 |
             v                 v
          Continue       Local buffer → background exporter → OTel Collector → backend
```

This matters most under load. At 10,000 requests/hour (~2.8 req/s) the request rate itself
isn't the problem — it's what each request generates. If each one produces 20 spans, that's
200,000 spans/hour (~56/s), which a properly designed pipeline handles fine, but a
synchronous-per-span exporter would not.

## Metrics are cheap, traces are not — sample accordingly

- **Metrics**: a counter increment is nearly free; batch-export every N seconds rather than
  per-event. Use broadly.
- **Traces**: one trace can contain many spans, so tracing every request multiplies cost
  fast. Sample instead — e.g. 1–10% of successful requests, 100% of errors and slow
  requests, 100% of specific high-value workflows. See [OpenTelemetry's sampling
  concepts](https://opentelemetry.io/docs/concepts/sampling/) for head vs. tail sampling
  strategies.

## Avoid high-cardinality metric labels

```
document_processing_duration{document_id="123456789"}   # bad: unbounded cardinality
document_processing_duration{operation="ocr", status="success"}   # good: bounded dimensions
```

Unique identifiers (request IDs, document IDs) belong in traces/logs, not metric label
values — see [Prometheus's own instrumentation best
practices](https://prometheus.io/docs/practices/naming/) on why unbounded labels blow up
storage and query cost.

> Metrics → aggregated information. Traces → one request's journey. Logs → detailed
> diagnostic context for one event.

## Fail open

The most important reliability principle: **a telemetry outage should never become an
application outage.**

```
Telemetry backend DOWN
          |
          v
Application
    |
    +-- business logic  -> CONTINUES
    +-- telemetry       -> buffered/dropped per policy, not blocking
```

If observability causes a meaningful throughput drop, or an outage in the observability
backend takes production down with it, that's a design/configuration problem, not an
inherent cost of instrumenting.

## Practical rules

1. Infrastructure metrics (CPU, memory, restarts) are usually collected externally — no app
   involvement needed.
2. Business/domain metrics need application involvement — infra can't infer them.
3. Never synchronously send telemetry from the critical path — async, batch, buffer.
4. Metrics are cheaper than traces — use metrics broadly, traces strategically and sampled.
5. Don't instrument every function — meaningful boundaries only.
6. Avoid high-cardinality labels — unique IDs go in logs/traces, not metric labels.
7. Telemetry should fail independently from the application.

## Reference

- [OpenTelemetry documentation](https://opentelemetry.io/docs/) — instrumentation SDKs,
  Collector, and the OTLP protocol referenced throughout this doc
- [OpenTelemetry: Sampling](https://opentelemetry.io/docs/concepts/sampling/) — head vs.
  tail sampling, the strategies referenced above
- [Prometheus: Instrumentation best practices](https://prometheus.io/docs/practices/naming/)
  — the cardinality guidance above
- [`observability-terminology.md`](observability-terminology.md) — what "telemetry",
  "observability", "span", "cardinality" actually mean
- [`observability-on-eks.md`](observability-on-eks.md) — which tools implement this on EKS,
  and its own [Responsibility matrix](observability-on-eks.md#responsibility-matrix) (tool
  → pillar, a different axis from the human responsibility split above)
- [`observability-otel-collector-and-datadog.md`](observability-otel-collector-and-datadog.md) —
  OTLP transport mechanics, Collector scaling, and the additional telemetry-specific failure
  modes (synchronous export, buffer exhaustion, OOMKill from telemetry buffers) that build
  on the critical-path and fail-open principles above
