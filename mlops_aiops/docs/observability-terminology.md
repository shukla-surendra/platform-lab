# Observability Terminology: Telemetry, Tracing, and the Vocabulary of "Why"

[`observability-on-eks.md`](observability-on-eks.md) explains which *tools* do what and
how they connect. This doc explains the *words* — what "telemetry," "observability,"
"tracing," "span," and "cardinality" actually mean, where they come from, and how they map
onto AWS/EKS specifics (CloudWatch above all) — because most confusion in this space isn't
about which product to pick, it's about two people using the same word to mean different
things. [`observability-instrumentation-tradeoffs.md`](observability-instrumentation-tradeoffs.md)
covers who's responsible for producing this telemetry and what it costs to do so.

## Telemetry — the umbrella term

**Telemetry** literally means "remote measurement" (Greek *tele* = remote, *metron* =
measure) — the term predates software entirely. A satellite or rocket sends telemetry back
to ground control: sensor readings, transmitted over distance, so operators on the ground
can know the state of something they can't directly touch. Metrics, logs, and traces are
exactly this, applied to software — your application is the rocket, your observability
backend is ground control, and "shipping telemetry" means the same thing in both contexts:
sending measurements about internal state to somewhere that can act on them.

## Monitoring vs. observability — a real, citable distinction, not just marketing

These get used interchangeably in casual conversation, but the distinction has real
origins and is worth holding onto precisely.

**Origin, verified**: "Observability" as a formal concept comes from **control theory** —
Rudolf Kálmán introduced it (alongside its dual, "controllability") in *"On the General
Theory of Control Systems,"* presented at the First IFAC Congress, Moscow, 1959/published
1960. The core idea: **a system is observable if its internal state can be inferred from
its external outputs over time.** That's the exact idea software borrowed decades later.

**Who brought it into software/DevOps, verified with exact quotes**:

- **Baron Schwartz** (VividCortex), *"Monitoring Isn't Observability"* (2017), traces it
  directly back to Kálmán and coins the line: *"Monitoring tells you whether the system
  works. Observability lets you ask why it's not working."*
- **Charity Majors** (Honeycomb co-founder), *"Observability: A Manifesto"*: *"Monitoring
  is about known-unknowns and actionable alerts, observability is about unknown-unknowns
  and empowering you to ask arbitrary new questions... without having to ship new code or
  gather new data."*

**The practical distinction that actually matters**: monitoring is watching **predefined**
signals for **predefined** failure modes you already thought to check ("alert if error
rate > 1%"). Observability is having enough raw telemetry, at enough granularity, that you
can answer a question you **never anticipated** — "why did requests from this one specific
customer, on this one specific browser version, start failing at 2:14pm" — after the fact,
without having built a dashboard for that exact scenario in advance. A system with great
dashboards can still have zero observability if nobody can debug a novel failure mode
without adding new instrumentation first.

## The three signal types, as terms (not tool names)

Already covered as an architecture in `observability-on-eks.md`; here's what each word
actually means, with an analogy:

- **Metric** — a numeric measurement, sampled repeatedly over time, usually with labels/
  dimensions attached (which pod, which endpoint). **Analogy: a car's speedometer.** One
  number, cheap to read continuously, tells you *that* something changed (speed dropped)
  but nothing about *why*.
- **Log** — a discrete, timestamped, immutable text record of a specific event.
  **Analogy: a ship captain's logbook.** Rich narrative detail about one moment, expensive
  to search through at volume, but it's where the actual story of what happened lives.
- **Trace** — the recorded path of **one single request** as it moves through multiple
  services. **Analogy: a package's delivery tracking history** — one tracking number,
  followed across every warehouse and truck it passed through, in order, with a timestamp
  at each stop.
- **Span** — one unit of work within a trace: one service's part of handling that request,
  with a start time, duration, and metadata. **Analogy: one leg of a relay race** — the
  trace is the whole race, each runner's leg is a span, and the baton itself is what proves
  the legs belong to the same race, not four unrelated sprints.

## Distributed tracing, in depth

### Trace ID, span ID, and context propagation

Every trace has a **trace ID** — a single identifier that every service touching that
request attaches to its own span, the way a package's tracking number stays the same at
every warehouse. Passing that ID forward from service to service (usually via an HTTP
header) is called **context propagation** — the literal baton pass in the relay-race
analogy: without it, each service would produce an orphaned span with no way to prove it
belongs to the same request as any other span.

**The standard, verified**: **W3C Trace Context** became an official **W3C Recommendation
on February 6, 2020**. It defines the `traceparent` HTTP header (carrying the trace ID,
parent span ID, and trace flags) plus a vendor-extensible `tracestate` header — this is
what [OpenTelemetry](tools/opentelemetry/README.md) uses by default, and what makes
instrumentation portable across backends.

**AWS X-Ray is the exception worth knowing about explicitly**: X-Ray's native header is
its own proprietary format, `X-Amzn-Trace-Id` — not W3C traceparent. As of an October 2023
AWS announcement, X-Ray now *accepts* W3C-format trace IDs from OpenTelemetry/ADOT
(converting internally), and OTel can send both headers at once — but X-Ray's own default
format is still proprietary, a real interoperability wrinkle if you're mixing X-Ray with
non-AWS tracing tooling.

### Sampling — why you almost never trace 100% of requests

Capturing a full trace for every single request is expensive at real volume, so tracing
systems **sample**. Two genuinely different strategies, both real and documented directly
by OpenTelemetry:

- **Head-based sampling** — the decision to trace a request is made **at the start**,
  before anything is known about the outcome. Simple and cheap, but by definition "can't
  sample spans with errors, because that information is not available when spans are
  created" (OpenTelemetry's own phrasing) — you might randomly skip tracing the exact
  request that later fails.
- **Tail-based sampling** — the decision is made **after** all spans in a request have
  completed, so you can deliberately keep every trace with an error or high latency
  regardless of a random sampling rate, and only randomly-sample the boring, fast,
  successful ones. More useful, but requires buffering all spans until a trace completes
  before deciding — real infrastructure cost for that flexibility.

## CloudWatch's own vocabulary, mapped to the generic terms

CloudWatch predates the current OpenTelemetry/Prometheus vocabulary and uses its own
words for the same underlying concepts — this mapping is the single most useful table for
not getting lost moving between AWS-native and open-source observability discussions:

| CloudWatch term | Generic / OTel-Prometheus equivalent | What it actually is |
|---|---|---|
| **Namespace** | Metric prefix / job label | A container grouping related metrics (e.g. `AWS/EC2`) |
| **Dimension** | Label / tag | A key-value pair identifying which specific resource a metric point describes (e.g. `InstanceId=i-0123`) |
| **Metric** | Metric / time series | Same concept — a named, dimensioned numeric measurement over time |
| **Log Group** | (no direct 1:1 equivalent — closest is a log "stream"/index scope) | A named collection of log streams, usually one per application/service |
| **Log Stream** | A single log source's sequence of entries | One sequence of log events from one source (e.g. one pod) within a Log Group |
| **Metric Filter** | Log-derived metric / recording rule | A pattern that extracts a metric value out of matching log lines, without needing the app to emit a separate metric call |
| **Embedded Metric Format (EMF)** | (AWS-specific — no direct equivalent) | A JSON log format letting you embed custom metrics directly inside structured log entries; CloudWatch auto-extracts them, so you pay for log ingestion instead of separate metric API calls |
| **Composite Alarm** | Alert rule combining multiple conditions | An alarm whose trigger condition is a boolean combination of other alarms |

## EKS-specific: how telemetry actually gets off a pod — sidecar vs. DaemonSet

Two genuinely different collection patterns, with a real responsibility trade-off, not
just a deployment detail:

- **DaemonSet collector** (Fluent Bit for logs, node-exporter for metrics, an OTel
  Collector in DaemonSet mode) — **one collector process per node**, shared by every pod
  scheduled there. Efficient (one process instead of N), but has no per-pod configuration —
  every pod on that node gets the same collection behavior.
- **Sidecar collector** — **one collector container per pod**, running alongside the
  application container in the same pod. More resource overhead (N collectors instead of
  one per node), but full per-pod isolation and configuration — useful when different
  workloads on the same node genuinely need different sampling rates, export destinations,
  or credentials.

Most metrics/log collection on EKS defaults to DaemonSet (cheaper, simpler); sidecars show
up more often for tracing specifically, where per-application sampling configuration
matters more.

## Tools mapped to responsibility (cross-reference)

Every tool named above has its own full write-up already in this repo:

| Signal | Open-source tools | AWS-native | Commercial |
|---|---|---|---|
| Metrics | [Prometheus](tools/prometheus/README.md) | [CloudWatch](tools/cloudwatch/README.md) Metrics | [Datadog](tools/datadog/README.md), [New Relic](tools/new-relic/README.md) |
| Logs | [Loki](tools/loki/README.md), [Elasticsearch](tools/elasticsearch/README.md) | CloudWatch Logs | [Splunk](tools/splunk/README.md), Datadog, New Relic |
| Traces | [Tempo](tools/tempo/README.md), [Jaeger](tools/jaeger/README.md) | AWS X-Ray | Datadog APM, New Relic APM |
| Instrumentation standard | [OpenTelemetry](tools/opentelemetry/README.md) | (X-Ray SDK, or OTel via ADOT) | (vendor SDKs, or OTel) |
| Visualization | [Grafana](tools/grafana/README.md) | CloudWatch Dashboards | Built into each commercial platform |

## Related docs in this repo

- [`observability-on-eks.md`](observability-on-eks.md) — the architecture/integration-flow
  layer this vocabulary sits underneath, including the full CloudWatch comparison.
- [`mlops-aiops-llmops.md`](mlops-aiops-llmops.md#aiops) — where this telemetry becomes the
  input to AIOps-style correlation/anomaly detection.
