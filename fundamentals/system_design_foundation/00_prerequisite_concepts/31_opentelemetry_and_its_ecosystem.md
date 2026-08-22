# Part 31: OpenTelemetry and Its Ecosystem

> This workspace already has excellent, thorough coverage of OTLP and the Collector's own
> architecture at
> [`../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md`](../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md)
> and
> [`../../../mlops_aiops/docs/tools/opentelemetry/README.md`](../../../mlops_aiops/docs/tools/opentelemetry/README.md) —
> cross-referenced throughout rather than repeated. This part covers what neither one
> does yet: the API-vs-SDK distinction, exactly how a trace ID crosses a network call,
> Semantic Conventions, and the OpenTelemetry Operator's actual injection mechanism —
> which turns out to be a concrete, real-world test of the sidecar-vs-init-container
> distinction [already taught in this workspace](../../../k8s_explorer/docs/sidecar-containers.md).

## In Plain English

Every tool [Parts 27-30](30_coalition_vs_unified_lgtm_signoz_openobserve.md) covered —
Prometheus, Loki, Tempo, SigNoz, OpenObserve — needs telemetry to already exist before it
can collect or store anything. OpenTelemetry is the answer to a question none of them
answer: **how does an application's code actually produce that telemetry in the first
place, in a way that doesn't lock the choice of backend in forever?** It's the vendor-
neutral "universal adapter" — instrument an application once, and the same telemetry can
be pointed at Tempo today, SigNoz tomorrow, and a commercial platform after that, without
touching the application's own code each time.

## The Problem, Precisely

Before OpenTelemetry, instrumenting an application meant picking a *vendor's* SDK —
Datadog's `dd-trace`, New Relic's agent — and that choice baked the backend into the
application's own code. Switching backends later meant re-instrumenting from scratch, not
a configuration change. OpenTelemetry (a CNCF project, formed by merging the earlier
OpenTracing and OpenCensus efforts) exists specifically to decouple those two decisions:
instrument against one vendor-neutral specification, decide *where the data goes* as a
separate, later, freely-changeable choice.

## The API vs. the SDK — a Distinction Worth Being Precise About

**OpenTelemetry is actually two layers, not one, and conflating them hides the exact
mechanism that makes "instrument once, switch backends freely" true**:

- **The API** — a stable, versioned interface (`tracer.start_span(...)`,
  `meter.create_counter(...)`) that application and library code calls directly. This is
  what gets baked into code, and it's deliberately minimal and stable across versions.
- **The SDK** — the actual, pluggable *implementation* behind that API: what really
  happens when `start_span()` is called, how spans are batched, sampled, and exported.

**Why the split matters mechanically**: application code depends only on the API.
Swapping which SDK is wired in underneath — a different sampling strategy, a different
exporter, even a no-op SDK for local testing — changes *nothing* in the instrumented
code itself, only which SDK the process loads at startup. This is the same
facade/interface-segregation idea already familiar from
[this repo's own LLD conventions](../../lld/05_rate_limiter/problem.md) (an interface
callers depend on, with swappable implementations behind it) — applied here to
instrumentation instead of application logic, and it's the actual mechanism (not just a
marketing claim) behind "OpenTelemetry avoids vendor lock-in."

**Placement note, extending this document series' own daemon/library distinction**:
**neither the API nor the SDK is a daemon** — both are libraries, linked directly into the
application's own process. Nothing about instrumenting code with OpenTelemetry starts a
separate process; the *only* separate process in this whole pipeline is the Collector
([already covered in depth elsewhere](../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md#the-opentelemetry-collector)),
which the SDK's background batch exporter sends data *to*.

## OTLP, Briefly — Fully Covered Elsewhere

**OTLP (OpenTelemetry Protocol) is the wire format, not the framework** — OpenTelemetry
is what you instrument with; OTLP is what carries the result to a Collector or any
OTLP-compatible backend, over gRPC (port 4317) or HTTP (port 4318). This distinction, the
full end-to-end path diagram, and the Collector's own DaemonSet-plus-central-tier scaling
pattern are already covered precisely in
[`observability-otel-collector-and-datadog.md`](../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md#otlp-the-protocol-not-the-framework) —
not re-derived here.

## Context Propagation — How a Trace ID Actually Crosses a Network Call

[Part 29 already named](29_the_rest_of_the_stack_grafana_tempo_alertmanager.md#tempo-and-jaeger-completing-the-third-pillar)
that a trace requires a shared trace ID "propagated through every downstream call, a
header passed hop to hop" — worth being precise about what that header actually contains.
The mechanism is a W3C standard, **Trace Context**, carried in an HTTP header literally
named `traceparent`:

```text
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             │  └────────────32 hex chars───────┘ └────16 hex chars─┘ │
           version         trace-id (16 bytes)   parent-id (8 bytes) flags
```

- **version** — the Trace Context spec version (`00`, currently the only defined value).
- **trace-id** — the same ID for *every* span in the entire request's journey, generated
  once at the entry point.
- **parent-id** — the *specific span ID* of whoever made this call, not the trace's ID —
  this is what lets a backend reconstruct the parent-child tree of which service called
  which, not just that they share a trace.
- **flags** — a bitfield; bit 0 is the sampled flag, telling a downstream service whether
  this trace was selected for collection (relevant to
  [Part 16's sampling coverage](16_observability.md#sampling-making-tracing-affordable-at-scale)).

**Every OpenTelemetry-instrumented HTTP/gRPC client and server automatically reads and
writes this header** as part of what the SDK does — an application developer doesn't
manually construct or parse `traceparent` in ordinary use; it's the concrete artifact
underneath the abstraction "the trace ID propagates automatically."

## Semantic Conventions — the Shared Vocabulary That Makes Cross-Tool Correlation Real

A genuinely easy-to-overlook piece: OpenTelemetry doesn't just standardize *how* telemetry
moves (OTLP) — it also standardizes *what attributes are called*, via **Semantic
Conventions**. A span for an HTTP request is expected to carry attributes named exactly
`http.request.method`, `http.response.status_code`, `url.path`; a database call carries
`db.system.name`, `db.query.text`; every span carries `service.name`. **Why this matters
practically**: without an agreed naming scheme, a dashboard or alert built against "status
code" would need separate logic per library, per language, per vendor, since each would
invent its own attribute name. With Semantic Conventions, a query written once — "show me
all spans where `http.response.status_code >= 500`" — works identically regardless of
which language, library, or OTel SDK produced the span. This is the specific mechanism
that makes "vendor-neutral" mean something concrete at query time, not only at
instrumentation time.

## The OpenTelemetry Operator — the Genuinely New Mechanics

The existing Collector doc names the Operator in a four-line diagram; here's the actual
mechanism, and why it's a precise real-world test of a distinction this workspace already
teaches in depth.

**What a Kubernetes Operator is, in general** — already covered at
[`../../../k8s_explorer/docs/crds-and-operators.md`](../../../k8s_explorer/docs/crds-and-operators.md):
a controller watching a Custom Resource Definition, reconciling the cluster's real state
toward whatever the CRD declares. The OpenTelemetry Operator provides two CRDs
specifically: `OpenTelemetryCollector` (declares and manages Collector instances) and
`Instrumentation` (declares auto-instrumentation configuration per language).

**The mechanism behind "inject instrumentation into supported pods," precisely**: the
Operator registers a **mutating admission webhook** — a piece of the Kubernetes API
server's request pipeline that can rewrite a resource *before* it's persisted. When a Pod
carrying a specific annotation
(e.g., `instrumentation.opentelemetry.io/inject-java: "true"`) is created, the webhook
intercepts it and modifies the Pod spec before scheduling ever happens. **This is where
the genuinely interesting precision lives — the Operator actually uses two different
injection patterns for two different jobs, not one:**

- **Auto-instrumentation injection is an *init container*, not a sidecar.** The webhook
  adds an `initContainers` entry that copies a language-specific agent (e.g., the OTel
  Java agent `.jar`) into a shared `emptyDir` volume, then exits — matching exactly [the
  "one-time setup, then exits" definition of a plain init container
  already established](../../../k8s_explorer/docs/sidecar-containers.md#sidecar-vs-init-container-vs-ambassadoradapter),
  not the "runs for the Pod's whole lifetime" definition of a sidecar. The webhook then
  also injects environment variables into the *main* application container
  (`JAVA_TOOL_OPTIONS=-javaagent:/otel-auto-instrumentation/javaagent.jar`) that make the
  application's own runtime load the copied agent at startup. Once the app process has
  started with the agent loaded, the init container's job is entirely done — it never
  runs again.
- **Deploying the Collector itself in "sidecar mode" is a genuine, continuously-running
  sidecar** — the *other* thing this same Operator can do, using the
  `OpenTelemetryCollector` CRD's `mode: sidecar` setting, injecting an always-running
  Collector container into the Pod, sharing its network so the app can send OTLP to
  `localhost` — this one *is* the textbook sidecar pattern, needing to be co-located
  specifically because it shares the Pod's network namespace with the app it's
  collecting from, [exactly the "needs the main container's own local access" test
  already established for Thanos and Loki's shipping agent](27_metrics_collection_and_scraping_mechanics.md#what-a-sidecar-actually-is-before-explaining-thanoss-own).

**The Operator process itself is also a daemon** — its own Deployment, watching the API
server continuously for matching Pods and CRDs, the same centralized-controller placement
already established for Metrics Server and kube-state-metrics
[in Part 27](27_metrics_collection_and_scraping_mechanics.md#how-kubernetes-does-this-five-distinct-pieces-not-one) —
not per-node, not itself injected into anything.

## Placement Summary — Library, Init Container, Sidecar, or Centralized Daemon

| Piece | What it actually is | Placement |
|---|---|---|
| OTel API | A library, linked into the app | Not a process at all |
| OTel SDK | A library, linked into the app | Not a process at all — the same process as the app |
| Auto-instrumentation agent | A file copied by an init container | Init container (runs once, exits) |
| Collector, sidecar mode | A genuine sidecar | One per Pod, co-located for `localhost` access |
| Collector, node-tier | A daemon | `DaemonSet`, one per node |
| Collector, central-aggregation tier | A daemon | Centralized Deployment |
| OpenTelemetry Operator | A daemon (Kubernetes controller) | Centralized Deployment, watching the API server |

## Designing and Operating From First Principles

- **Reach for auto-instrumentation (the init-container path) when engineering time is the
  scarce resource, not runtime overhead** — it trades some control and precision for zero
  code changes; manual instrumentation via the API/SDK directly is the right choice when a
  team needs specific custom spans/attributes an agent's generic injection can't produce.
- **Budget instrumentation effort by language, using the existing quality table
  [already documented](../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md#auto-instrumentation-quality-varies-sharply-by-language)** —
  Java/Python/.NET's runtime-injection capability makes the auto-instrumentation path
  genuinely turnkey; Go/Rust's static compilation means budgeting real engineering time
  for manual instrumentation instead.
- **Adopt Semantic Conventions even for custom, hand-written spans**, not only when using
  auto-instrumentation — a hand-instrumented span using `http.response.status_code`
  instead of an invented `statusCode` field is what keeps a dashboard built once working
  against every service, auto-instrumented or not.

## Key Takeaways

- **OpenTelemetry is two layers — a stable API applications code against, and a
  pluggable SDK behind it** — the actual mechanism, not just a claim, behind "instrument
  once, switch backends without touching code."
- **Neither the API nor the SDK is a daemon — both are libraries inside the app's own
  process.** The Collector is the only separate process in the whole pipeline.
- **A trace ID crosses a network call via the W3C `traceparent` HTTP header**, carrying a
  version, the shared trace ID, the *specific* parent span ID, and a sampled flag — not an
  abstract "shared context," a concrete header with a defined byte layout.
- **Semantic Conventions standardize attribute *names*, not just the transport** — the
  specific mechanism that makes a query or dashboard built once actually work across
  languages, libraries, and vendors.
- **The OpenTelemetry Operator uses two genuinely different injection patterns for two
  different jobs** — auto-instrumentation via a one-shot init container plus env-var
  injection, and Collector deployment via a real, continuously-running sidecar — a
  concrete test of the sidecar-vs-init-container distinction this workspace already
  teaches in the abstract.

## Quick Self-Check

- Explain, precisely, why swapping which OTel SDK a service uses doesn't require any
  change to that service's own instrumented code.
- A `traceparent` header carries a trace-id and a parent-id. What's the difference
  between the two, and what would be lost if only the trace-id were included?
- The OpenTelemetry Operator's auto-instrumentation injection uses an init container, not
  a sidecar, while its Collector-injection mode uses a genuine sidecar. Justify both
  choices using the same "does it need the main container's own local access,
  continuously" test already established for Thanos and Loki's shipping agent.
- Why does a dashboard built against `http.response.status_code` keep working when a new
  service, written in a different language with a different auto-instrumentation agent,
  is added to the system?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **API-vs-SDK framing (the default opener for "how does OTel avoid lock-in"):**
  "OpenTelemetry splits into a stable API applications code against and a pluggable SDK
  underneath it — swapping the SDK's export destination changes nothing in the
  instrumented code itself, which is the actual mechanism behind vendor neutrality, not
  just a marketing claim."
- **Concrete-header framing (good for demonstrating depth on trace propagation):** "A
  trace ID isn't an abstract shared context — it's a specific HTTP header, `traceparent`,
  with a defined byte layout carrying a version, the trace ID, the calling span's own ID,
  and a sampled flag. Every OTel-instrumented client and server reads and writes it
  automatically."
- **Two-injection-patterns framing (good for showing depth on the Operator
  specifically):** "The OpenTelemetry Operator actually uses two different Kubernetes
  patterns for two different jobs — an init container for one-shot auto-instrumentation
  agent delivery, and a genuine sidecar for Collector deployment — which is a clean,
  concrete test of when each pattern is actually the right one, not an arbitrary
  implementation detail."

### Vocabulary Builder

- **mutating admission webhook** (n. phrase) — a Kubernetes API server extension point
  that rewrites a resource before it's persisted; the mechanism behind the OpenTelemetry
  Operator's pod injection.
- **Semantic Conventions** (n. phrase, OTel-specific) — OpenTelemetry's standardized
  attribute naming scheme, ensuring the same concept (an HTTP status code, a database
  system) carries the identical attribute name regardless of language or library.
- **`traceparent`** (n., W3C Trace Context) — the specific HTTP header carrying a trace's
  shared ID and the calling span's own ID between services.
- **"…is a library, not a daemon"** — the precise, reusable distinction for placing the
  OTel API/SDK correctly against every genuinely separate process this document series
  covers (the Collector, the Operator, every centralized backend).

---

**Previous:** [Part 30: Coalition vs. Unified — LGTM, SigNoz, OpenObserve](30_coalition_vs_unified_lgtm_signoz_openobserve.md)  |  **Next:** [0. The Interview Framework](../01_ml_system_design/00_interview_framework_fundamentals.md)
