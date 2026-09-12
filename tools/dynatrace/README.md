# Dynatrace

**Category:** observability / monitoring (commercial, all-in-one)

## What it is

A commercial, SaaS, all-in-one observability platform — metrics, logs, distributed
tracing (APM), infrastructure monitoring, and a built-in AIOps-style causal AI engine
called **Davis AI**, all under one product and one bill, in the same all-in-one category
as [Datadog](../datadog/README.md) and [New Relic](../new-relic/README.md).

## What it's used for

- **Full-stack, auto-discovered observability** — the OneAgent installs once per host and
  automatically discovers processes, services, and their dependencies, rather than
  requiring hand-configured instrumentation per service. Same "fastest path to full
  observability" trade-off as Datadog's agent-based install.
- **Davis AI** — Dynatrace's differentiator versus Datadog/New Relic: a **deterministic,
  causal AI engine** (not purely statistical anomaly detection) that builds a real-time
  topology map of every host/process/service dependency and uses it to pinpoint a single
  root cause among the noise during an incident, rather than surfacing a ranked list of
  correlated anomalies for a human to interpret. This is the specific capability named
  alongside Splunk ITSI, Moogsoft, Datadog Watchdog, and BigPanda as a commercial
  AIOps-branded correlation/anomaly-detection/root-cause layer in
  [`mlops-aiops-llmops.md`](../../mlops-aiops-llmops.md#aiops).
- Accepts [OpenTelemetry](../opentelemetry/README.md) (OTLP) data, same as Datadog and New
  Relic, so existing OTel instrumentation isn't locked out.
- Strong presence in large enterprise/regulated environments (its OneAgent + topology-map
  approach originated from application performance monitoring for complex, legacy-heavy
  infrastructure estates), which is part of why it's a name that comes up in the same
  breath as Splunk/Datadog/New Relic during enterprise vendor evaluations.

## Deployment combinations seen in practice

Dynatrace isn't used one fixed way — which combination applies changes what it's actually
competing with and where its value shows up most:

- **Standalone all-in-one (most common)** — OneAgent replaces the entire self-hosted stack
  outright: no Prometheus, no Grafana, no Loki/ELK, no Jaeger/Tempo. One agent per host
  auto-discovers metrics, logs, traces, and APM together, with Davis AI on top. This is the
  "buy, don't build" choice — the same category decision as picking Datadog or New Relic
  instead of assembling the open-source stack.
- **Dynatrace + OpenTelemetry** — teams that already standardized on OTel instrumentation
  for portability send OTLP data into Dynatrace as the backend, instead of (or alongside)
  OneAgent's own auto-instrumentation. Keeps the instrumentation vendor-neutral while still
  getting Davis AI's causal engine on top.
- **Dynatrace + Kubernetes/EKS (OneAgent as a DaemonSet)** — deployed per-node on the
  cluster, auto-discovering every pod/service/container and rebuilding the topology map live
  as pods churn. This is where the causal-AI root-cause value is strongest, since "which of
  40 pods actually caused this" is exactly the problem Davis AI's topology model targets.
- **Dynatrace layered alongside a cloud-native baseline, not replacing it** — some large
  enterprises keep CloudWatch or a baseline Prometheus setup for cost/compliance reasons on
  certain workloads, and add Dynatrace only where deep APM/root-cause analysis is worth the
  spend. Less common (it gives up some of the "one bill" simplicity) but shows up in orgs
  running legacy and modern estates side by side, consistent with Dynatrace's enterprise
  positioning above.
- **Not typically combined with Datadog/New Relic/Splunk for the same telemetry** — these
  are substitutes for each other in the all-in-one category, not complements; running two of
  them over the same services means paying for and maintaining two overlapping platforms
  rather than getting additive value.

## Trade-off vs. the self-hosted stack

Same shape of trade-off as [Datadog](../datadog/README.md)/[New Relic](../new-relic/README.md)
vs. Prometheus+Grafana+Loki: comparatively little setup and operational burden, at the cost
of vendor lock-in and a cost model that scales with hosts/data volume rather than
infrastructure provisioned and owned directly. Dynatrace specifically tends to price and
position itself toward large enterprise estates rather than smaller/self-serve teams,
versus Datadog's broader self-serve-friendly pricing.

## Alternatives

- **Datadog / New Relic** — closest competitors in the all-in-one commercial category; the
  main practical difference is Davis AI's deterministic causal topology model versus
  Datadog Watchdog's more statistical anomaly-detection approach. See
  [Datadog](../datadog/README.md), [New Relic](../new-relic/README.md).
- **Splunk** — stronger SIEM/security-log roots rather than APM/causal-AI roots; see
  [Splunk](../splunk/README.md).
- **Self-hosted**: Prometheus + Grafana + Loki/Elasticsearch + Tempo/Jaeger — full control
  and portability, at the cost of operating it yourself and building any correlation/root-
  cause layer on top separately. See [`observability-on-eks.md`](../../observability-on-eks.md)
  for that comparison in depth.

## Related

- [`observability-on-eks.md`](../../observability-on-eks.md) — where commercial platforms
  fit relative to the self-hosted and AWS-native paths.
- [`mlops-aiops-llmops.md`](../../mlops-aiops-llmops.md#aiops) — Davis AI as a named example
  of a commercial AIOps-branded correlation/root-cause layer, in the context of Gartner's
  AIOps definition and the broader analyst disagreement on what "AIOps platform" means.
