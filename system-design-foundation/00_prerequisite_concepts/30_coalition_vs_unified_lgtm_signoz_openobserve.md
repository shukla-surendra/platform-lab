# Part 30: Coalition vs. Unified — LGTM/Mimir, SigNoz, and OpenObserve

> Names the architectural fork [Parts 27-29](27_metrics_collection_and_scraping_mechanics.md)
> already built one whole side of, without ever naming it as a choice: a **coalition** of
> specialized, purpose-built stores (Prometheus/Mimir + Loki + Tempo + Grafana) vs. a
> **single unified store** for every signal (SigNoz, OpenObserve). This part adds the
> mechanics existing tool notes in this repo don't cover, and the comparison across the
> fork itself — not a re-explanation of facts already documented well elsewhere, which are
> cross-referenced throughout rather than repeated.

## In Plain English

Two ways to staff the security desk from
[Part 29's analogy](29_the_rest_of_the_stack_grafana_tempo_alertmanager.md#in-plain-english).
Option one: hire three specialists — a headcount tracker, a transcript archivist, a
visitor-badge auditor — each excellent at their one job, coordinated through one shared
front desk. Option two: hire *one* generalist who keeps everything in a single ledger —
less specialized at any one thing, but only one person to manage, train, and pay. Neither
is strictly better; they're a genuine trade-off between per-signal optimization and
operational simplicity, and this part is about naming that trade-off precisely rather than
treating either side as the obvious default.

## The Problem, Precisely — the Fork This Part Names Explicitly

[Parts 27-29](27_metrics_collection_and_scraping_mechanics.md) built out, in full
mechanical detail, exactly *one* branch of a real architectural fork: a purpose-built
store per signal (Prometheus/Mimir for metrics, Loki for logs, Tempo for traces), each
indexed differently because [Part 28 already established](28_log_collection_mechanics_loki.md#why-what-existed-before-loki-and-the-specific-bet-loki-makes)
that different data shapes want different index strategies. The other branch bets the
opposite way: **one general-purpose store, good enough at every signal's access patterns
that the operational cost of running three separate specialized systems isn't worth
paying.** Neither SigNoz nor OpenObserve invents new collection mechanics to do this —
the fork is a *storage-layer* decision, not a collection-layer one, worth stating
precisely before looking at either.

## Where Mimir and "LGTM" Actually Fit — a Precision Worth Restating

Mimir and the LGTM name are already documented in full in this repo's own tool notes —
[`../../../mlops_aiops/docs/tools/mimir/README.md`](../../../mlops_aiops/docs/tools/mimir/README.md)
and
[`../../../mlops_aiops/docs/tools/lgtm-stack/README.md`](../../../mlops_aiops/docs/tools/lgtm-stack/README.md) —
not re-derived here. **One correction worth carrying forward precisely, since it's easy to
get backwards**: those docs are explicit that **Prometheus is not one of the four LGTM
letters**. Mimir is the metrics *backend* — a Prometheus-`remote_write`-compatible,
PromQL-answering long-term store, exactly the third option [Part 27's own remote_write
section already named](27_metrics_collection_and_scraping_mechanics.md#the-downstream-direction-prometheus-as-a-push-client-remote_write)
alongside Thanos and Cortex. Prometheus itself, if used at all, sits *in front of* Mimir
as the scraper — an optional fifth piece, not the "M."

**The mechanics those existing docs don't cover, extending Part 27's own treatment**:
Mimir is explicitly *not* one monolithic process — its documented "microservices
architecture" splits into independently scalable components (a distributor accepting
writes, ingesters holding recent data, queriers answering reads, a compactor, a
store-gateway serving from object storage) — each its own Deployment. Every one of them is
**centralized, never a `DaemonSet`** — the identical placement logic
[already established three times now](27_metrics_collection_and_scraping_mechanics.md#is-prometheus-itself-a-daemon)
for Prometheus, Loki, and Tempo, simply split across more independently-scalable pieces
than a single Prometheus server is.

## SigNoz — the Mechanics Beyond What's Already Documented

SigNoz's own architecture (ClickHouse as the single store for all three signals,
OTel-native from day one, MIT-core-plus-proprietary-`ee/`-licensing) is already covered in
full at
[`../../../mlops_aiops/docs/tools/signoz/README.md`](../../../mlops_aiops/docs/tools/signoz/README.md) —
not repeated here. **The genuinely new point worth making**: SigNoz ships its own
distribution of the **OpenTelemetry Collector**, which follows the *exact same*
DaemonSet-plus-central-aggregation-tier pattern
[already covered in Part 29](29_the_rest_of_the_stack_grafana_tempo_alertmanager.md#otel-collector-and-the-exporter-ecosystem-briefly-cross-referenced-rather-than-re-derived)
and in
[`../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md`](../../../mlops_aiops/docs/observability-otel-collector-and-datadog.md).
**SigNoz doesn't invent new collection mechanics — it reuses the identical OTel Collector
architecture, just pointed at ClickHouse instead of fanning out to three separate
backends.** This is the clearest possible demonstration that the coalition-vs-unified fork
lives entirely in the *storage* layer: collection (push vs. pull, agent placement,
DaemonSet vs. centralized) is unaffected by which side of the fork a stack takes.

## OpenObserve — Genuinely New Ground

Not yet documented anywhere in this workspace — the following is first-principles
coverage, not a cross-reference to existing depth.

**Why**: the exact same bet [Part 28 already covered for Loki](28_log_collection_mechanics_loki.md#what-lokis-actual-architecture) —
object storage as the *primary*, native durability layer from day one, not a bolted-on
extension — but **generalized to all three signals at once, not only logs.** Where Loki
made this bet for one signal and the rest of the LGTM stack still needed Mimir/Tempo to
separately adopt the same philosophy, OpenObserve makes it the *entire system's*
foundation from the start: metrics, logs, and traces all land in the same
S3/GCS/Azure-Blob-backed store, which is the direct source of its stated pitch — petabyte-
scale retention at a cost structure close to raw object storage pricing, not a specialized
database's.

**What**: a single binary (written in Rust), OTLP-compatible for ingestion, with its own
built-in UI (dashboards, alerting, log/trace/metric correlation) — though, like SigNoz, it
can also be queried through Grafana if an org already standardized on that UI. Internally
it keeps a lightweight index over the object-stored data — the same "index the cheap
dimension, defer the expensive part to query time" philosophy this whole document series
keeps finding, applied here across every signal type at once rather than per-signal.

**Where**: because it's a single binary rather than a coalition of specialized components,
deployment is dramatically simpler than either LGTM (4+ separately-run pieces) or even
SigNoz (Collector + ClickHouse + query service + frontend, at minimum) — a single
OpenObserve process (or a small cluster of them, for HA/scale) is the whole system. No
per-signal backend to separately provision, size, or upgrade.

**How**: telemetry arrives via OTLP (or OpenObserve's own native ingestion APIs), gets
written directly to object storage with a lightweight index alongside it, and queries hit
that index first to narrow the search before reading the relevant object-storage data —
mechanically the closest analog to Loki's own label-index-then-chunk-scan approach
[already covered in Part 28](28_log_collection_mechanics_loki.md#what-lokis-actual-architecture),
just applied uniformly across metrics and traces too, not only logs.

**Distinguishing it from SigNoz precisely, since both get casually lumped together as
"unified alternatives"**: SigNoz bets on **ClickHouse** — a real columnar OLAP database,
faster at complex aggregate queries, but you're paying for compute-plus-storage together,
not cheap object storage alone. OpenObserve bets on **object storage directly** as the
primary store — cheaper at rest, simpler operationally (no database cluster to run), at
the cost of the query performance a purpose-built OLAP engine like ClickHouse can offer.
Two different implementations of "unify the signals," not one monolithic alternative to
LGTM — worth naming which specific trade-off is actually being chosen, not just "a unified
platform" as a category.

## Master Comparison: The Fork, All the Way Across

| | LGTM (Prometheus/Mimir + Loki + Tempo + Grafana) | SigNoz | OpenObserve |
|---|---|---|---|
| Storage philosophy | One specialized store per signal | One ClickHouse (OLAP database) for all three | One object-storage-backed system for all three |
| Number of components to run | 4+ (Mimir alone splits into several) | 4 (Collector, ClickHouse, query service, frontend) | 1 binary (or a small HA cluster of it) |
| Collection mechanics | OTel Collector or native scrapers/shippers, `DaemonSet`-plus-central-tier | Same OTel Collector pattern, its own distribution | OTLP-compatible, same general pattern |
| Query language(s) | PromQL + LogQL + TraceQL (three, one per signal) | SQL-flavored, via SigNoz's own UI/API over ClickHouse | Its own query API/UI, SQL-flavored |
| Primary durable store | Object storage, per-signal (Mimir/Loki/Tempo each independently) | ClickHouse's own storage (can itself sit on object storage, but the query engine is the primary interface) | Object storage, directly, system-wide |
| Maturity / battle-testing | Each component individually mature, widely deployed at scale | Newer, smaller-scale deployments than LGTM's individual pieces | Newest of the three, least battle-tested at extreme scale |
| Best fit | Teams already invested in Prometheus/Grafana, or needing per-signal tuning headroom | Teams wanting one platform, OTel-native, willing to run/scale ClickHouse | Teams prioritizing lowest possible storage cost and operational footprint over query performance headroom |

## Designing and Operating From First Principles

- **The fork is a storage decision — evaluate it as one, not as "which product is
  better."** Collection mechanics (push/pull, `DaemonSet` placement, OTLP) are identical
  regardless of which side is chosen, per SigNoz's own reuse of the standard OTel
  Collector — the actual decision is entirely about what happens to data *after* it's
  collected.
- **"Fewer components to run" is a real, legitimate reason to prefer a unified platform**
  for a small team without dedicated observability-infrastructure capacity — this is the
  same "question whether the harder path is actually needed" instinct already applied to
  rate limiting and metrics retention elsewhere in this repo, now applied to the choice
  between four specialized backends and one.
- **Don't treat "unified" as one option** — SigNoz (ClickHouse, query-performance-first)
  and OpenObserve (object storage, cost-first) make genuinely different trade-offs inside
  the same broad category; naming which specific one applies is what separates a real
  evaluation from a marketing-page comparison.

## Key Takeaways

- **LGTM is not Prometheus + Loki + Tempo + Grafana — it's Mimir, not Prometheus, as the
  "M."** Prometheus, if present, is an optional scraper sitting in front of Mimir, not
  one of the four named components.
- **Mimir's own architecture is itself a coalition of independently-scalable
  microservices** (distributor, ingester, querier, compactor, store-gateway) — the same
  centralized, never-`DaemonSet` placement already established for every store in this
  document series, just split across more pieces.
- **SigNoz doesn't reinvent collection — it reuses the standard OTel Collector
  architecture and points it at one database instead of three**, proof that the
  coalition-vs-unified choice lives entirely in the storage layer.
- **OpenObserve generalizes Loki's own "object storage native from day one" bet to every
  signal, not just logs** — the same architectural philosophy, applied system-wide instead
  of per-signal.
- **SigNoz and OpenObserve are not the same kind of "unified"** — ClickHouse (a real
  database, faster, costs compute+storage together) vs. object storage directly (cheaper,
  simpler, less query headroom) are two different implementations of the same broad idea.

## Quick Self-Check

- Correct this sentence precisely: "The LGTM stack is Prometheus, Grafana, Tempo, and
  Mimir." What's wrong, and where does Prometheus actually sit if it's used at all?
- Explain why SigNoz's use of the standard OTel Collector, rather than inventing its own
  collection mechanism, is evidence that the coalition-vs-unified fork is a storage
  decision, not a collection decision.
- OpenObserve is often described as "the Loki philosophy, generalized." What specifically
  is being generalized, and to which signals does OpenObserve apply it that Loki alone
  does not?
- A small team with no dedicated observability engineer is choosing between LGTM and a
  unified platform. Name the specific trade-off they're actually making, in terms of
  component count and per-signal optimization.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Storage-not-collection framing (the default opener):** "The coalition-versus-unified
  choice between LGTM and something like SigNoz or OpenObserve lives entirely in the
  storage layer — SigNoz reuses the exact same OTel Collector architecture everyone else
  does, it just writes to one ClickHouse instead of fanning out to three specialized
  backends. Collection mechanics don't change based on this decision."
- **Generalized-Loki framing (good for explaining OpenObserve specifically):**
  "OpenObserve is Loki's own object-storage-native bet, generalized past logs to every
  signal at once — the same philosophy Part 28 already covers for one signal, now applied
  system-wide."
- **Two-different-unifieds framing (good for avoiding a shallow SigNoz-vs-OpenObserve
  answer):** "I wouldn't treat 'unified platform' as one category — SigNoz bets on a real
  OLAP database for query performance, OpenObserve bets on raw object storage for cost and
  operational simplicity. Naming which specific trade-off is actually in play is the
  difference between an evaluation and a marketing comparison."

### Vocabulary Builder

- **microservices architecture** (n. phrase, as applied to Mimir) — splitting a system
  into independently deployable, independently scalable components (distributor,
  ingester, querier, etc.) rather than one monolithic process — the same word used
  generally in [Part 20](20_microservices_architecture_patterns.md), now a concrete
  instance inside an observability backend itself.
- **OLAP (Online Analytical Processing)** (n. phrase) — a database architecture
  (ClickHouse is one) optimized for aggregate queries over large volumes (group-by,
  percentile, time-range scans) rather than single-row lookups — the specific property
  SigNoz's bet depends on.
- **"…is a storage decision, not a collection decision"** — the precise, reusable phrase
  for keeping the coalition-vs-unified fork correctly scoped to where it actually lives.

---

**Previous:** [Part 29: The Rest of the Stack — Grafana, Tempo, Alertmanager](29_the_rest_of_the_stack_grafana_tempo_alertmanager.md)  |  **Next:** [Part 31: OpenTelemetry and Its Ecosystem](31_opentelemetry_and_its_ecosystem.md)
