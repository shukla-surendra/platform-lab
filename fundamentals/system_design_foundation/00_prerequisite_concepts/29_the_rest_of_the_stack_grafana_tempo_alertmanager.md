# Part 29: The Rest of the Stack — Grafana, Tempo, Alertmanager, and the Exporter Ecosystem

> Completes the picture [Part 27](27_metrics_collection_and_scraping_mechanics.md)
> (metrics) and [Part 28](28_log_collection_mechanics_loki.md) (logs) built — the
> visualization layer that unifies both, the third pillar (traces) neither one covers,
> and the component that actually pages someone when something's wrong. Same
> why/what/where/how treatment, reusing every concept those two parts already
> established rather than re-deriving it.

## In Plain English

Extend [Part 27's office-building analogy](27_metrics_collection_and_scraping_mechanics.md#in-plain-english)
one step further. There's a room-headcount tracker (Prometheus) and a transcript archive
(Loki) — now add a **security desk with monitors for both**, so nobody has to walk to two
separate rooms to check each one (**Grafana**). Add a **visitor badge that's scanned at
every door a specific person walks through**, so you can reconstruct exactly which rooms
one visit touched and how long each stop took (**Tempo**, tracing). And add an **alarm
system** that doesn't just display a number on a screen but actually calls someone's phone
when a threshold is crossed (**Alertmanager**) — because a dashboard nobody is looking at
at 3am doesn't help anyone.

## The Problem, Precisely

Metrics ([Part 27](27_metrics_collection_and_scraping_mechanics.md)) tell you *that*
something changed — error rate spiked at 14:32. Logs
([Part 28](28_log_collection_mechanics_loki.md)) tell you the detail of one specific
event. Neither tells you, in a request that touched twelve microservices, **which one of
them actually added the latency** — that needs following *one specific request's* path
across every hop it made, which is what a **trace** is (already introduced conceptually
in [Part 16's Three Pillars](16_observability.md#the-three-pillars); this part covers the
mechanism). And none of the three signals, on their own, **tells a human anything** unless
someone is actively staring at a dashboard when the problem happens — turning "a number
crossed a threshold" into "a person's phone rang" is a distinct job, done by a distinct
component, not something Prometheus does by itself despite frequently being credited with
it.

## Grafana — Why, What, Where, How

**Why**: without a unifying layer, you'd need Prometheus's own basic built-in web UI for
metrics, a separate tool for logs (Loki ships none of its own), and yet another for
traces — three logins, three mental contexts, no way to correlate a metric spike with the
logs from the same moment without manually matching timestamps by hand. Grafana exists
specifically to make "one dashboard, panels from three different backends, one shared time
range" possible.

**What**: **purely a query-and-visualization layer — it stores none of the telemetry data
itself**, the exact generalization of [Part 27's own point about Grafana and
Prometheus](27_metrics_collection_and_scraping_mechanics.md#grafana-doesnt-store-metric-data-it-queries-on-demand-no-worker-involved):
the same "queries on demand, keeps nothing" relationship holds for Loki and Tempo too, not
only Prometheus. Grafana's own database (SQLite by default, Postgres/MySQL for production)
holds dashboard JSON, data-source connection settings, user accounts, and alert-*rule*
definitions — never metric samples, log lines, or spans.

**Where**: runs as an ordinary **Deployment** — centralized, not per-node, not a sidecar —
for the same reason Prometheus and Loki are centralized: it's a shared query surface
for the *whole* system, and there's no per-node or per-pod local resource it needs
exclusive access to. In practice it usually ships **bundled in the `kube-prometheus-stack`
Helm chart alongside Prometheus, Alertmanager, node-exporter, and kube-state-metrics** —
one install wires Grafana to Prometheus automatically; Loki and Tempo are typically added
afterward as additional data sources.

**How**: a browser (or the Grafana server itself, for a scheduled report) requests a
dashboard → Grafana issues one query per panel to whichever backend that panel is
configured against — PromQL to Prometheus, LogQL to Loki, TraceQL to Tempo — merges the
results, and renders them together, on one shared time-range slider. Nothing is fetched
until asked; nothing is retained after rendering.

## Tempo (and Jaeger) — Completing the Third Pillar

**Why**: the specific gap neither metrics nor logs can close — "this request took 800ms;
which of the 12 services it touched actually spent that time." Requires a shared
**trace ID**, generated once at the request's entry point and propagated through every
downstream call (a header passed hop to hop), so every service's individually-recorded
span can be stitched back into one timeline afterward.

**What, and the pattern worth naming explicitly**: Tempo (Grafana's own tracing backend)
deliberately does **not** build a full-text/tag index over every span attribute the way
some tracing backends do — it's designed to be found primarily by trace ID (arriving from
a log line, or a **metric exemplar** — a sample trace ID Prometheus can attach to one
specific histogram observation, letting a latency-spike panel link straight to the exact
trace that caused it) or via structural TraceQL queries, keeping storage cheap the same
way Loki does. **This is the third instance of the identical pattern this document series
keeps finding**: Loki is "Prometheus's cheap-index philosophy, applied to logs"
([Part 28](28_log_collection_mechanics_loki.md#why-what-existed-before-loki-and-the-specific-bet-loki-makes));
Tempo is the same philosophy applied to traces. Jaeger is the older, still widely used
alternative tracing backend, taking a comparatively heavier full-indexing approach closer
to Elasticsearch's own trade-off in the logs space.

**Where**: centralized, object-storage-backed from day one — the same **Deployment/
StatefulSet, not `DaemonSet`** placement already established twice now for Loki and
Prometheus, for the identical reason: one unified store for the whole cluster's traces,
not one per node.

**How**: application code — auto-instrumented or manually instrumented via the
OpenTelemetry SDK — emits spans carrying the shared trace ID, sent via **OTLP** to the
**OpenTelemetry Collector**, which exports them onward to Tempo. **This exact pipeline,
including the Collector's own DaemonSet-plus-central-tier scaling pattern, is already
covered in full in
[`../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md`](../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md)**
— not re-derived here; that doc is the authoritative deep-dive on OTLP, the Collector's
own architecture, and auto-instrumentation quality trade-offs across languages.

## Alertmanager — the Separate Component Most People Conflate with Prometheus

**Why this is worth a dedicated section**: [Part 27 already named "alerting" as one of
the four things Prometheus does that a bare exporter doesn't](27_metrics_collection_and_scraping_mechanics.md#why-prometheus-when-all-these-other-tools-already-expose-data),
but that's imprecise stated that way — **Prometheus only *evaluates* alert rules**
(continuously checking "is this PromQL expression currently true"). It does not decide
who gets notified, how to avoid paging the same person five times for five related
symptoms of one root cause, how to temporarily silence a known issue, or which channel
(Slack vs. PagerDuty vs. email) a given severity should reach. **That's Alertmanager's
job — a genuinely separate component**, not a feature bundled inside Prometheus itself.

**What Alertmanager actually does, precisely**:

- **Grouping** — bundling multiple related firing alerts (e.g., the same symptom across
  20 pods) into *one* notification instead of 20 separate pages.
- **Deduplication** — if multiple Prometheus replicas (an HA pair) both evaluate the same
  rule and both fire, Alertmanager collapses that into one notification, not two.
- **Silencing** — a human can temporarily mute a known, already-being-worked issue without
  editing or removing the underlying alert rule.
- **Inhibition** — suppress a *downstream* alert automatically when a known *root-cause*
  alert is already firing (e.g., don't page separately for "every service is down" once
  "the whole cluster is unreachable" has already fired).
- **Routing** — sending different alerts to different receivers based on their labels
  (severity, team, service).

**Where**: its own small, centralized Deployment/StatefulSet — not per-node, not a
sidecar — capable of running as a small HA cluster (its replicas gossip with each other
directly to stay deduplicated across instances). Ships in the **same
`kube-prometheus-stack` Helm chart as Grafana**, the concrete fact already named above —
one install, both components wired in together by default.

**How**: Prometheus evaluates its alert rules on the same scrape-interval schedule it
already runs on; when a rule's condition is true, Prometheus **pushes** the firing alert
to Alertmanager's own API — worth noting explicitly that this relationship is itself
**push** (Prometheus is the client here, Alertmanager the server receiving the post), a
third instance of the push-vs-pull distinction this document series keeps drawing
precisely, alongside Loki's Promtail-push and Prometheus's own `remote_write`-push.
Alertmanager then applies grouping/dedup/silence/inhibition/routing rules and sends the
result to whichever receiver is configured — a webhook, Slack, PagerDuty, email.

## OTel Collector and the Exporter Ecosystem — Briefly, Cross-Referenced Rather Than Re-Derived

**The OpenTelemetry Collector** — the pipeline component sitting between "telemetry was
generated" and "telemetry is queryable somewhere," receiving OTLP and able to batch,
filter, transform, sample, and fan data out to multiple backends at once, with its own
DaemonSet-per-node-plus-central-aggregation-tier scaling pattern — is already covered in
full depth in
[`../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md`](../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md),
not repeated here.

**The wider exporter ecosystem, beyond what Parts 27-28 already named** (node-exporter,
cAdvisor, kube-state-metrics):

- **blackbox-exporter** — probes a target *from the outside* (HTTP, TCP, ICMP), reporting
  whether it's reachable and how long that took — a fundamentally different vantage point
  from every exporter covered so far, which all report *from inside* the thing being
  measured. Useful for exactly the failure mode where the target itself can't self-report
  because it's the network path to it that's actually broken.
- **`mysqld-exporter` / `postgres-exporter`** — database-specific metrics (connection pool
  usage, query latency, replication lag) that only the database's own internals expose;
  the same "someone has to expose data in Prometheus's format before it can be scraped"
  principle from Part 27, applied per-database-engine.
- **`dcgm-exporter`** — worth naming precisely since this session already installed and
  used the underlying daemon by hand: `dcgm-exporter` is a **separate, Prometheus-format
  wrapper** around the same `nv-hostengine` process
  [installed and queried directly via `dcgmi` earlier this session](../../../../mini-llms-playground/infra/gcp-gpu-node/docs/dcgm_gpu_command_reference.md)
  — the CLI tool (`dcgmi`) is for interactive diagnostics; `dcgm-exporter` is the daemon
  that exposes the identical underlying GPU telemetry as a scrapeable `/metrics` endpoint,
  the same exposer role node-exporter and cAdvisor already play, specifically for GPU
  fleets.

## Master Comparison: Every Component Across Parts 27-29

| Component | Signal | Placement | Collection direction |
|---|---|---|---|
| Prometheus | Metrics | `StatefulSet`, centralized | Pull (scrapes targets) |
| Loki | Logs | `StatefulSet`, centralized | Push (Promtail → Loki) |
| Tempo | Traces | `StatefulSet`/Deployment, centralized | Push (Collector → Tempo) |
| Grafana | Visualization (all three) | Deployment, centralized | Pull (queries all three, on demand) |
| Alertmanager | Alert routing/notification | Deployment, centralized | Push (Prometheus → Alertmanager) |
| OTel Collector | Telemetry pipeline | `DaemonSet` (node tier) + Deployment (central tier) | Receives push (OTLP), forwards onward |
| node-exporter / cAdvisor / `dcgm-exporter` | Metric sources | `DaemonSet` | Exposed; pulled by Prometheus |

## Designing and Operating From First Principles

- **Name which component actually "did" an alerting decision, precisely, in an
  interview or an incident retro.** "Prometheus alerted us" is imprecise — Prometheus
  *evaluated* the condition; Alertmanager *decided* how (or whether) that became a human
  notification. Conflating the two hides a real, separately-operated component from the
  conversation.
- **Reach for a metric exemplar before manually correlating a dashboard spike with a
  trace by timestamp.** If Prometheus and Tempo are both wired up, the linkage already
  exists mechanically — a spike's exemplar points at a real trace ID directly, no
  timestamp-matching guesswork needed.
- **Treat `kube-prometheus-stack`'s bundling as a starting default, not a permanent
  coupling.** Grafana, Prometheus, and Alertmanager shipping together in one Helm chart
  is a convenience, not an architectural requirement — each is independently swappable
  (Grafana for Amazon Managed Grafana, Alertmanager for a different routing layer)
  without touching the others.

## Key Takeaways

- **Grafana stores none of the telemetry it displays, for any of the three signals** —
  the same "queries live, keeps nothing" property Part 27 established for its Prometheus
  relationship generalizes to Loki and Tempo too.
- **Tempo is the third instance of the same pattern**: Prometheus's cheap-index
  philosophy, applied first to logs (Loki), now to traces (Tempo) — index the cheap,
  bounded dimension (labels, trace ID), leave the expensive part unindexed until query
  time.
- **Alertmanager, not Prometheus, decides who gets paged** — grouping, deduplication,
  silencing, inhibition, and routing are all a separate component's job, reached via a
  push relationship (Prometheus is the client, Alertmanager the server) that's easy to
  overlook when people say "Prometheus alerted us."
- **Every centralized component in this series (Prometheus, Loki, Tempo, Grafana,
  Alertmanager) is a `Deployment`/`StatefulSet`, never a `DaemonSet`** — the daemons in
  this whole stack are specifically the *collection-layer* pieces (node-exporter,
  Promtail, the OTel Collector's node tier) that need per-node local access; everything
  downstream of collection is centralized by design.

## Quick Self-Check

- A dashboard shows a latency spike. Walk through, precisely, how to get from that panel
  to the exact trace responsible, naming which component does what at each step.
- "Prometheus paged the on-call engineer." What's imprecise about that sentence, and
  which two separate components and which separate relationship (push or pull) does it
  actually involve?
- Why is Tempo described as applying "the same pattern as Loki" — what specifically is
  the shared design philosophy, and which earlier tool did it originate from in this
  document series?
- Name a metrics source that reports on a target *from outside* it, rather than from
  inside — why does that vantage point matter, and what failure mode does it catch that
  an inside-reporting exporter structurally cannot?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Query-layer-stores-nothing framing (the default opener for Grafana specifically):**
  "Grafana is a pure query and rendering layer across every signal — metrics, logs,
  traces — it stores none of them itself. Its own database only holds dashboard
  definitions and configuration, the same relationship Prometheus already has with it,
  generalized to Loki and Tempo too."
- **Same-philosophy-three-times framing (good for showing depth on Tempo specifically):**
  "Tempo is the third time this stack applies the identical idea — index only the cheap,
  bounded dimension, defer the expensive part to query time. Prometheus does it for
  metric labels, Loki does it for log labels, Tempo does it for trace IDs — recognizing
  that repetition is more valuable than knowing any one of the three in isolation."
- **Separate-component framing (good for the alerting question specifically):** "I'd
  correct 'Prometheus alerted us' to name both components precisely — Prometheus
  evaluates the rule and pushes the result, Alertmanager decides grouping, dedup,
  silencing, and routing before anything reaches a human. Treating that as one step
  hides a real operational boundary."

### Vocabulary Builder

- **exemplar** (n., Prometheus/Tempo-specific) — a sample trace ID attached to one
  specific metric observation, letting a dashboard panel link directly to the exact
  trace responsible for an outlier value.
- **inhibition** (n., Alertmanager-specific) — automatically suppressing a downstream
  alert because a known root-cause alert is already firing, to avoid paging separately
  for every symptom of one underlying failure.
- **TraceQL** (n.) — Tempo's own structural query language for traces, the trace-pillar
  analog of PromQL (metrics) and LogQL (logs).
- **"…evaluates the condition; a separate component decides who's paged"** — the fluent,
  precise way to correct the common conflation of Prometheus's alert-rule evaluation with
  Alertmanager's actual notification decision.

---

**Previous:** [Part 28: Log Collection Mechanics — Loki](28_log_collection_mechanics_loki.md)  |  **Next:** [Part 30: Coalition vs. Unified — LGTM/Mimir, SigNoz, and OpenObserve](30_coalition_vs_unified_lgtm_signoz_openobserve.md)
