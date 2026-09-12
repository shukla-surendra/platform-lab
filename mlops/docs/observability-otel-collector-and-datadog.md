# OTLP, the OpenTelemetry Collector, and Datadog

[`observability-terminology.md`](observability-terminology.md) covers what the words mean;
[`observability-on-eks.md`](observability-on-eks.md) covers which self-hosted tools do what;
[`observability-instrumentation-tradeoffs.md`](observability-instrumentation-tradeoffs.md)
covers who's responsible for instrumenting and what it costs. This doc fills the piece none
of those own: the actual transport mechanics between an instrumented app and a backend
(OTLP, the Collector), and the fully-managed alternative to self-hosting that stack
(Datadog) — including where it genuinely still needs custom instrumentation and where it
doesn't.

## The full path, end to end

```text
Application
    ↓
Instrumentation
    ↓
Telemetry (metrics, logs, traces)
    ↓
OTel SDK
    ↓
OTLP
    ↓
OpenTelemetry Collector
    ↓
Metrics backend / Logs backend / Trace backend
    ↓
Grafana
```

**Instrumentation** generates telemetry as part of the application's own execution path —
creating and updating a span happens inline with the code being measured. **Exporting**
that telemetry is normally decoupled: the SDK queues it, a background batch exporter drains
the queue, and only that background process talks to the network. This is why a span
`start()`/`end()` pair is cheap even though shipping it over gRPC is not — the two are not
the same step. (The reliability implications of getting this wrong — synchronous export
blocking the request path, and why telemetry should fail open rather than take the app down
with it — are covered in `observability-instrumentation-tradeoffs.md`, not repeated here.)

## OTLP — the protocol, not the framework

**OpenTelemetry (OTel)** is the framework/ecosystem: SDKs for instrumenting code, the
Collector for processing telemetry, and a specification covering all three signal types.
**OTLP (OpenTelemetry Protocol)** is narrower — just the wire protocol that carries
telemetry between an SDK, a Collector, and any OTLP-compatible backend. Conflating the two
is the most common confusion in this space: OpenTelemetry is what you instrument with; OTLP
is what carries the result.

OTLP runs over either:

- **gRPC** — conventionally port **4317**
- **HTTP** — conventionally port **4318**

Both carry the same signal types (traces, metrics, logs); the choice is usually about what
a given network path or Collector deployment already supports, not a difference in
capability.

## Auto-instrumentation quality varies sharply by language

Kubernetes can inject OpenTelemetry auto-instrumentation into supported pods via the
**OpenTelemetry Operator**, without the application explicitly calling the SDK:

```text
Kubernetes
    ↓
OpenTelemetry Operator
    ↓
Inject instrumentation into supported pods
    ↓
Application starts, telemetry generated automatically
    ↓
OTel Collector
```

How well this actually works depends heavily on the runtime:

| Language | Auto-instrumentation experience |
|---|---|
| Java | Excellent |
| Python | Excellent |
| .NET | Excellent |
| Node.js | Good |
| Go | More limited |
| Rust | More limited |

The reason Rust and Go lag here isn't OpenTelemetry immaturity — it's that Java, Python, and
.NET all support runtime bytecode/interpreter-level instrumentation injection, so an agent
can wrap function calls after the binary is already running. Rust and Go compile to a
static binary with no such injection point, so instrumentation has to be integrated through
libraries at *build* time instead of attached at *runtime*. Budget for that difference when
estimating instrumentation effort on a Rust service versus a Java one — it's not a rounding
error.

## The OpenTelemetry Collector

The Collector is the piece that sits between "telemetry was generated" and "telemetry is
queryable somewhere." It receives OTLP, and can:

- Batch and filter telemetry before forwarding it
- Transform or add attributes
- Sample (drop a controlled fraction to cut volume/cost)
- Route different signals to different backends
- Export to multiple backends simultaneously

```text
Multiple Pods
   │  OTLP
   ↓
OpenTelemetry Collector
   │
   ├──→ Metrics backend
   ├──→ Logs backend
   └──→ Traces backend
```

### Scaling it

At real Kubernetes scale — hundreds or thousands of pods — a single Collector instance
becomes its own bottleneck. The common pattern is two tiers:

```text
                    ┌── Pod
                    ├── Pod
Node 1 ── OTel ─────┤   (node-local Collector, DaemonSet)
                    └── Pod

                    ┌── Pod
                    ├── Pod
Node 2 ── OTel ─────┤
                    └── Pod
                         │
                         ↓
                  Central Collectors  (aggregation, further processing)
                         │
                    ┌────┼────┐
                    ↓    ↓    ↓
                 Metrics Logs Traces
```

A per-node Collector (DaemonSet — one pod per node, the same pattern Promtail uses for logs
in `observability-on-eks.md`) does cheap local batching close to the source; a central
Collector tier handles heavier aggregation and fan-out to backends. If you operate the
Collector yourself, its capacity and scaling are now your responsibility too — it's another
stateful-ish component in the critical path of "can I see what's happening," not a
zero-maintenance sidecar.

## Grafana vs. Datadog — the actual axis of comparison

`observability-on-eks.md` already covers Grafana's own stack (Prometheus, Loki, Tempo).
The comparison worth having explicitly is Grafana-stack vs. a fully managed platform:

| | Grafana (self-hosted stack) | Datadog |
|---|---|---|
| Dashboards | Yes | Yes |
| Metrics/logs/traces collection | Usually external (Prometheus/Loki/Tempo/etc.) | Built-in (Agent) |
| Metrics/logs storage | Usually external, self-operated | Built-in, managed |
| APM | Via other components (Tempo + instrumentation) | Built-in |
| Kubernetes/infra monitoring | Via integrations | Built-in |
| Operational complexity | Higher if self-hosting the full stack | Lower |
| Cost model | Infra cost, scales with what you run | SaaS cost, scales with hosts/data volume |

The honest framing: **Grafana is primarily the visualization/query layer** — it queries
whatever backend you point it at, on a refresh interval (a "live" 5-second-refresh
dashboard is just Grafana re-querying Prometheus/Loki every 5 seconds, not a push
subscription). **Datadog is a complete platform** — collection, storage, search,
correlation, and visualization all owned by one vendor. The tradeoff is the standard
self-hosted-vs-managed one: more control and usually lower infra cost with Grafana's stack,
less operational burden and a predictable-but-growing SaaS bill with Datadog.

## Datadog, briefly

```text
Application / Kubernetes
        ↓
Datadog Agent (DaemonSet) / OpenTelemetry
        ↓
Datadog Platform
   ┌────┼────┬──────┐
   ↓    ↓    ↓      ↓
 Metrics Logs Traces Profiles
   └────┼────┴──────┘
        ↓
    Datadog UI — Dashboards / Search / Alerts / APM
```

The **Datadog Agent** runs as a DaemonSet, the same deployment shape as Promtail or a
node-local OTel Collector, and collects node/pod metrics, container restarts, Kubernetes
events, logs, and application telemetry from every node it runs on.

**APM (Application Performance Monitoring)** — the discipline this doc otherwise doesn't
name directly — is what answers "why is my application slow," by breaking one request down
into its component latencies:

```text
POST /receipt                         2.0 sec
│
├── Authentication                     50 ms
├── Preprocessing                     300 ms
├── OCR                              1,500 ms
└── Database write                     150 ms
```

### What still needs custom instrumentation, even with Datadog

Datadog's auto-instrumentation covers infrastructure and most application-framework-level
telemetry (HTTP, DB queries, common libraries) with little or no code change. It does not,
and cannot, know your business semantics:

```text
Level 1 — Infrastructure         → mostly automatic
  CPU, memory, disk, pods, nodes, k8s events

Level 2 — Application            → often automatic with APM
  HTTP requests, DB queries, RPC, errors, latency

Level 3 — Business               → usually manual instrumentation
  domain counters, custom workflow state, model/version info
```

This is the same limitation named in `observability-instrumentation-tradeoffs.md` §1 —
"if understanding the domain is required, the application has to expose that information
itself" — restated here because it's specifically the thing a Datadog sales conversation
can make sound solved when it isn't. If `model_version` or a domain-specific outcome field
matters, someone still writes `span.set_attribute(...)` for it, agent or no agent.

## A cross-discipline note: MLflow autologging is instrumentation too

`mlflow.autolog()` is worth naming explicitly as an instance of the same general concept
this doc is about, even though it has nothing to do with OpenTelemetry:

```text
ML training code
   ↓
MLflow Autologging
   ↓
Instrumentation
   ↓
MLflow tracking data (params, metrics, model, dataset info, duration, environment)
   ↓
MLflow Tracking Server
```

"Instrumentation" is the general mechanism of making software emit information about what
it's doing; OpenTelemetry is one implementation of that idea for services, and MLflow's
autologging is a separate, unrelated implementation of the same idea for training runs.
They don't interoperate and shouldn't be confused for the same system, but recognizing them
as the same *concept* is useful — it's the pattern to look for the next time a new tool
claims to add "observability" to something: what's the instrumentation, what's the
telemetry, and where does it get queried.

## Failure modes specific to telemetry itself

Beyond the general fail-open principle (`observability-instrumentation-tradeoffs.md`),
these are the concrete ways telemetry specifically has been observed to degrade or freeze
an application, worth checking for by name during an incident:

1. **Synchronous export** — telemetry generation blocking on a network call to the
   Collector. A slow or unreachable Collector then directly slows the application.
2. **Queue/buffer exhaustion** — telemetry produced faster than it can be exported;
   memory grows until telemetry starts being dropped, or the process does.
3. **Excessive span creation** — instrumenting very small, very high-frequency operations
   creates real CPU/memory overhead from the instrumentation itself, not just its export.
4. **High-cardinality attributes** — `request_id`, `user_id`, or similar unique values used
   as metric labels create unbounded series counts (see `observability-instrumentation-tradeoffs.md`
   §"Avoid high-cardinality metric labels" for why this is expensive specifically for
   *metrics* backends).
5. **Exporter/instrumentation library bugs** — a blocking call, deadlock, or leak inside the
   telemetry library itself, not the application code, taking the app down with it.
6. **Memory pressure from telemetry buffers** — buffered-but-unexported telemetry counts
   against the same container memory limit as the application, and can trigger an OOMKill
   that reads as an application bug when the actual cause is telemetry backpressure.

## Reference

- [OpenTelemetry: OTLP specification](https://opentelemetry.io/docs/specs/otlp/) — the
  transport protocol details (ports, gRPC vs. HTTP) referenced above
- [OpenTelemetry Collector documentation](https://opentelemetry.io/docs/collector/) —
  configuration, processors, and deployment patterns for the Collector itself
- [`observability-terminology.md`](observability-terminology.md) — what "span," "trace,"
  "telemetry" mean as words
- [`observability-on-eks.md`](observability-on-eks.md) — the self-hosted Grafana/Prometheus/
  Loki/Tempo stack this doc's Grafana-vs-Datadog comparison assumes
- [`observability-instrumentation-tradeoffs.md`](observability-instrumentation-tradeoffs.md) —
  who's responsible for instrumenting what, critical-path export, sampling, cardinality,
  and the fail-open principle this doc's failure-modes section builds on
