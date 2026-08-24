# Kubernetes Observability & Prometheus — Learning Summary

## 1. Core mental model

```text
Kubernetes / EKS
│
├── Application Pods ── /metrics ──────────┐
│                                          │
├── kubelet + cAdvisor ─ /metrics/cadvisor │
│                                          │
├── GPU nodes ── DCGM Exporter ─ /metrics  │
│                                          ▼
└── other exporters ─────────────────── Prometheus
                                             │
                                             ▼
                                      Prometheus TSDB
                                             │
                                             ▼
                                          Grafana
```

The important idea is that there are **different sources of metrics** — application
code, the kubelet, GPU nodes, and anything else running an exporter — all feeding one
collector rather than each having its own separate monitoring path.

---

## 2. Prometheus

Prometheus is primarily a:

- Metrics scraper/collector
- Time-series database
- Query engine
- Monitoring/alerting component

Its normal model is **pull-based**:

```text
Prometheus ── GET /metrics ──► Target
```

Prometheus normally does not expect applications to push metrics directly to it —
Prometheus reaches out on a schedule, rather than every target being responsible for
remembering to send data somewhere.

---

## 3. Metrics vs logs vs traces

These are different observability signals:

```text
Metrics → Prometheus / Mimir / AMP etc.
Logs    → Loki / OpenSearch / Elasticsearch etc.
Traces  → OpenTelemetry / Tempo / Jaeger etc.
```

This document focuses on **metrics**.

---

## 4. Prometheus TSDB

TSDB means **Time-Series Database**.

Prometheus has its own built-in TSDB. It does not require PostgreSQL, MySQL, etc. by
default.

A time series is a sequence of timestamped values:

```text
Metric              Time       Value
--------------------------------------
gpu_temperature     10:00:01   70
gpu_temperature     10:00:02   71
gpu_temperature     10:00:03   72
```

Prometheus TSDB uses concepts such as:

- Blocks
- WAL (Write-Ahead Log)
- Index
- Compressed chunks

Mental model:

```text
WHAT stores metrics?
        ↓
Prometheus TSDB
```

---

## 5. Kubernetes storage for Prometheus

The TSDB is the storage engine; Kubernetes storage determines where its files live.

Typical production setup:

```text
Prometheus Pod
      │
      ▼
     PVC
      │
      ▼
     PV
      │
      ▼
    AWS EBS
```

So:

```text
TSDB = how Prometheus stores metrics
PVC/PV/EBS = where the TSDB files live
```

Without persistent storage, deleting the Pod can lose locally stored data.

---

## 6. remote_write

Prometheus can forward metrics to an external backend:

```text
Prometheus
   │
   ├── Local TSDB
   │
   └── remote_write ──► External metrics backend
```

`remote_write` sends **metrics**, not logs.

Possible backends include:

- Amazon Managed Service for Prometheus (AMP)
- Grafana Mimir
- Thanos-based architectures
- Cortex

---

## 7. Self-hosted Prometheus and scaling

If Prometheus is self-hosted in Kubernetes, you are responsible for:

- CPU
- Memory
- Persistent storage
- Retention
- Scrape frequency
- Number of targets
- Availability
- Upgrades
- Recovery
- Scaling

Prometheus scaling is not simply:

```text
Prometheus Pod → HPA → many replicas
```

A stock Prometheus is not horizontally scalable by just adding replicas — two
independent Prometheus Pods each scrape and store their own separate copy of
everything, not a shared, deduplicated dataset. Large environments instead reach for
remote storage or a purpose-built scalable metrics system (see §6 and §8).

---

## 8. Amazon Managed Service for Prometheus (AMP)

AWS provides a managed Prometheus-compatible backend.

Conceptually:

```text
EKS
 │
 ├── Metrics collector / Prometheus
 └── Exporters
          │
          │ remote_write
          ▼
        AMP
          │
          ▼
       Grafana
```

The distinction:

```text
Self-hosted Prometheus
    → You operate the metrics backend

AMP
    → AWS operates the managed backend
```

---

## 9. GPU metrics: DCGM Exporter

GPU nodes need a GPU-specific exporter — cAdvisor and node-exporter (§1, §11) don't
understand GPU internals at all, so without DCGM Exporter, GPU utilization, memory,
temperature, and ECC errors simply have no metric source.

**DCGM Exporter** exposes NVIDIA GPU metrics in Prometheus format. It's commonly
deployed as a **DaemonSet**, so there's one exporter Pod per GPU node — the same
node-scoped pattern cAdvisor follows (§10), for the same reason: the thing being
measured is physically local to that node.

```text
Node 1
└── DCGM Exporter ── :9400/metrics

Node 2
└── DCGM Exporter ── :9400/metrics

Node 3
└── DCGM Exporter ── :9400/metrics
```

Each exporter exposes its own `/metrics` endpoint; Prometheus discovers and scrapes
each one independently — there is no single central GPU-metrics endpoint for the whole
cluster, mirroring the same "node-specific, not all-node" point made about
`/metrics/cadvisor` in §15:

```text
Service Discovery
       │
       ├── DCGM Exporter — Node 1
       ├── DCGM Exporter — Node 2
       └── DCGM Exporter — Node 3
                     │
                     ▼
                Prometheus
```

**So DCGM Exporter is normally node-level, not one central endpoint** — same shape as
kubelet/cAdvisor, different metrics. For the deeper DCGM material (deployment modes,
`dcgmi` CLI, health monitoring, `nvidia-smi` vs. DCGM) see
[`observability-gpu-monitoring-dcgm-triton.md`](observability-gpu-monitoring-dcgm-triton.md)
and a real worked deployment — DaemonSet, `ServiceMonitor`, `PrometheusRule` alerts,
troubleshooting — in
[`../../manual_notes/gpu-cluster-monitoring-lab.md`](../../manual_notes/gpu-cluster-monitoring-lab.md).

---

## 10. Metrics by level

Pulling §1 through §9 together — four levels, four different metric sources, none of
them substitutable for another:

| Level | Metrics | Typical source |
|---|---|---|
| Node | CPU, memory, disk, network | node-exporter |
| Container/Pod | CPU, memory, network, filesystem | kubelet/cAdvisor |
| GPU | utilization, temperature, memory, errors | DCGM Exporter |
| Application | requests, latency, errors, business metrics | Application `/metrics` |

A cluster can be fully healthy at three of these levels and still be failing at the
fourth — which is exactly why all four get scraped into the same Prometheus rather
than picking just one as "the" monitoring signal.

---

# cAdvisor

## 11. What is cAdvisor?

cAdvisor (Container Advisor) provides **container resource metrics**, such as:

- CPU usage
- Memory usage
- Network traffic
- Filesystem usage
- CPU throttling

Think:

> **cAdvisor = container resource metrics**

It is not the application itself and it is not the database storing historical
metrics.

---

## 12. Where does cAdvisor run?

Modern Kubernetes integrates cAdvisor functionality into the **kubelet**.

Conceptually:

```text
Kubernetes Node
│
└── kubelet
      │
      └── cAdvisor functionality
            │
            ├── observes Container A
            ├── observes Container B
            └── observes Container C
```

There is not normally a separate cAdvisor sidecar inside every application Pod.

Historically, standalone cAdvisor deployments were also commonly run as a DaemonSet,
but the key modern mental model is:

> **kubelet contains cAdvisor functionality and observes containers on its node.**

---

## 13. Does cAdvisor expose metrics?

Yes.

The cAdvisor metrics are exposed through the kubelet's cAdvisor metrics endpoint,
commonly:

```text
/metrics/cadvisor
```

The flow is:

```text
Container
   │
   ▼
cAdvisor
   │
   ▼
kubelet
   │
   ▼
/metrics/cadvisor
   │
   ▼
Prometheus
```

Example metrics:

```text
container_cpu_usage_seconds_total
container_memory_working_set_bytes
container_network_receive_bytes_total
```

---

## 14. cAdvisor is not a database

cAdvisor provides the metrics; Prometheus stores them.

```text
cAdvisor
   │
   │ container resource metrics
   ▼
Prometheus
   │
   ▼
Prometheus TSDB
```

So:

```text
cAdvisor   = metrics provider
Prometheus = scraper + storage + query engine
```

---

# Minikube and node-level cAdvisor

## 15. Three-node Minikube setup

The environment discussed has:

```text
minikube       → Control Plane
minikube-m02   → Worker
minikube-m03   → Worker
```

Each node has a kubelet and therefore its own cAdvisor functionality:

```text
minikube
 └── kubelet
      └── cAdvisor

minikube-m02
 └── kubelet
      └── cAdvisor

minikube-m03
 └── kubelet
      └── cAdvisor
```

---

## 16. Accessing cAdvisor in Minikube

Start a local Kubernetes API proxy:

```bash
kubectl proxy --port=8001
```

Then access a specific node's cAdvisor metrics:

```bash
kubectl get --raw "/api/v1/nodes/minikube/proxy/metrics/cadvisor"
```

For workers:

```bash
kubectl get --raw "/api/v1/nodes/minikube-m02/proxy/metrics/cadvisor"
kubectl get --raw "/api/v1/nodes/minikube-m03/proxy/metrics/cadvisor"
```

The path:

```text
/api/v1/nodes/<NODE>/proxy/metrics/cadvisor
```

means:

> Go through the Kubernetes API server to that node's kubelet and request its cAdvisor
> metrics.

---

## 17. `/metrics` is not all-node metrics

After running:

```bash
kubectl proxy --port=8001
```

this:

```text
http://127.0.0.1:8001/metrics
```

is **not a combined metrics endpoint for all Kubernetes nodes**.

It is the metrics endpoint of the component being addressed through that URL, such as
the Kubernetes API server itself.

For cAdvisor metrics use:

```text
/api/v1/nodes/<node>/proxy/metrics/cadvisor
```

So:

```text
/metrics
    ↓
API server metrics

/api/v1/nodes/minikube/proxy/metrics/cadvisor
    ↓
minikube kubelet/cAdvisor metrics
```

---

# Pod-level metrics

## 18. "Pod metrics" has two meanings

This distinction is critical.

### A. Pod/container resource metrics

Examples:

- CPU
- Memory
- Network
- Filesystem

These come from cAdvisor/kubelet:

```text
Pod
 │
 ▼
Container runtime
 │
 ▼
cAdvisor
 │
 ▼
kubelet /metrics/cadvisor
 │
 ▼
Prometheus
```

You do **not** contact the Pod itself for these resource metrics.

### B. Application metrics

These are metrics produced by the application itself:

```text
http_requests_total
inference_requests_total
request_latency_seconds
orders_processed_total
```

The application can expose:

```text
http://<pod>:8080/metrics
```

Prometheus then scrapes that endpoint:

```text
Application Pod
      │
      │ /metrics
      ▼
  Prometheus
```

Therefore:

> **cAdvisor tells you how much resource the container/Pod is consuming.**
>
> **Application `/metrics` tells you what the application is doing.**

---

# Application metrics and scaling

## 19. What happens when Pods scale?

Suppose a Deployment has three replicas:

```text
Deployment: my-app
│
├── Pod A → /metrics
├── Pod B → /metrics
└── Pod C → /metrics
```

Do not manually configure Prometheus with Pod IPs:

```text
pod-a-IP:8080/metrics
pod-b-IP:8080/metrics
pod-c-IP:8080/metrics
```

Pod IPs are temporary.

Instead, Prometheus uses **Kubernetes service discovery**.

Conceptually:

```text
Kubernetes API
      │
      │ discover Pods
      ▼
  Prometheus
      │
      ├── Pod A /metrics
      ├── Pod B /metrics
      └── Pod C /metrics
```

If the Deployment scales from 3 to 5:

```text
Pod A
Pod B
Pod C
Pod D
Pod E
```

Kubernetes discovery detects the new Pods and Prometheus starts scraping them.

If a Pod disappears, Prometheus stops scraping that target.

Therefore:

> **Pod scaling does not require manually changing Prometheus target configuration.**

---

## 20. How does Prometheus know which Pods to scrape?

Prometheus can use Kubernetes service discovery.

Common Kubernetes-native approaches include:

- Kubernetes service discovery
- Prometheus Operator
- `ServiceMonitor`
- `PodMonitor`

Conceptually:

```text
PodMonitor
    │
    │ selects matching Pods
    ▼
Pod A ── /metrics
Pod B ── /metrics
Pod C ── /metrics
```

When Pods scale, discovery updates the targets automatically — nobody edits a
`ServiceMonitor`/`PodMonitor` object when a Deployment's replica count changes.

---

## 21. Why scrape each Pod separately?

Suppose:

```text
Pod A → 100 requests
Pod B → 500 requests
Pod C → 200 requests
```

Prometheus can retain Pod identity:

```text
http_requests_total{pod="A"} ...
http_requests_total{pod="B"} ...
http_requests_total{pod="C"} ...
```

Then PromQL can aggregate:

```promql
sum(http_requests_total)
```

or calculate rates:

```promql
rate(http_requests_total[5m])
```

This allows both:

- Per-Pod analysis
- Deployment-wide analysis

---

## 22. Application custom metrics

You don't need a separate metrics server for every Pod — the application exposes its
own `/metrics` next to its normal traffic port, using one of two common paths:

### Prometheus client library

```text
Application
   ↓
Prometheus client library
   ↓
/metrics
   ↓
Prometheus
```

The direct route: the app links a Prometheus client library, defines counters/gauges/
histograms in code, and the library handles rendering them at `/metrics` in the format
Prometheus expects.

### OpenTelemetry

```text
Application
   ↓
OpenTelemetry SDK
   ↓
OpenTelemetry Collector
   ↓
Metrics / Traces / Logs
```

The broader route: OpenTelemetry isn't Prometheus-specific — the same instrumentation
can emit metrics, traces, *and* logs together, with the Collector then exporting
metrics onward to Prometheus (among other possible backends). A Prometheus client
library only ever produces metrics; OpenTelemetry is the choice when the same
instrumentation should also feed tracing (see the tracing material in
`manual_notes/Observability in AI Infrastructure.md`, Part 6).

---

# Consuming Prometheus data elsewhere

## 23. Kubernetes Service Discovery vs. Prometheus Adapter

These two look similar (both sit between Prometheus and Kubernetes) but move data in
**opposite directions**, and confusing the two is a common source of "why isn't my HPA
scaling on this metric" confusion.

### Service Discovery

```text
Kubernetes → Prometheus
```

Tells Prometheus:

> Here are the Pods/targets to scrape.

This is everything covered in §19–§20 — Kubernetes feeding Prometheus a target list.

### Prometheus Adapter

```text
Prometheus → Kubernetes
```

Prometheus Adapter works in the *opposite* direction: it makes selected Prometheus
metrics available back through Kubernetes' own metrics APIs (the same API surface
`kubectl top` and the Horizontal Pod Autoscaler read from) — useful specifically for
**HPA/custom autoscaling** on a metric Prometheus computed (e.g. request queue depth)
rather than only the built-in CPU/memory metrics Kubernetes tracks natively.

```text
Application
    ↓
Prometheus
    ↓
Prometheus Adapter
    ↓
Kubernetes Metrics API
    ↓
HPA
    ↓
Scale Deployment
```

Mental model:

> **Service Discovery helps Prometheus find metrics** (Kubernetes → Prometheus).
>
> **Prometheus Adapter helps Kubernetes consume Prometheus metrics** (Prometheus →
> Kubernetes).

---

# Alerting

## 24. Prometheus Alertmanager

Prometheus itself evaluates alert rules — a PromQL expression plus a threshold:

```yaml
- alert: HighCPU
  expr: cpu_usage > 90
  for: 5m
```

When Prometheus determines a rule's condition is true (and has stayed true for the
`for:` duration — the same pattern used in the DCGM alert rules in
`manual_notes/gpu-cluster-monitoring-lab.md`), it sends the alert onward to
**Alertmanager**:

```text
Prometheus
    │
    │ alert fires
    ▼
Alertmanager
    ├── Email
    ├── Slack
    ├── PagerDuty
    └── Webhook
```

Alertmanager itself doesn't decide *when* something is wrong — that's Prometheus's
job. Alertmanager's job starts after that: it provides

- Routing
- Grouping
- Deduplication
- Silencing
- Inhibition
- Notification delivery
- Resolved notifications

i.e. turning "this condition fired" into "the right person got exactly one useful
notification," rather than every matching rule paging every channel individually. The
important distinction:

> **Prometheus decides WHEN an alert condition is true.**
>
> **Alertmanager decides HOW and WHERE to notify.**

Alertmanager can send real notifications through an SMTP server, Slack webhook,
PagerDuty integration, or a generic webhook — see
[Part 7 of `manual_notes/Observability in AI Infrastructure.md`](../../manual_notes/Observability%20in%20AI%20Infrastructure.md#part-7--building-alerts-for-ai-system-failures)
for alert design (thresholds, actionability, avoiding alert fatigue) beyond this
document's scope.

---

## 25. Prometheus vs. Kibana

A common observability split, and a frequent point of confusion for anyone coming from
a single-vendor stack that bundles both:

```text
Metrics
  ↓
Prometheus
  ↓
Alertmanager
  ↓
Email / Slack / PagerDuty
```

and:

```text
Logs
  ↓
Elasticsearch
  ↓
Kibana
  ↓
Log investigation / log-based alerting
```

Prometheus/Alertmanager are generally used for **metrics-based alerting**.

Kibana/Elastic are commonly used for **log search, investigation, and log-based
alerting**.

They are complementary, not competing — a metrics alert tells you *that* something is
wrong and roughly where; the logs (via Kibana, or Grafana+Loki as this repo's own
[`log-stack/`](../../k8s_observability/log-stack/) chart uses instead) are usually
where you go next to find out *why*.

---

# Final mental model

```text
                         Kubernetes Cluster
                                  │
       ┌──────────────────────────┼──────────────────────────┐
       │                          │                          │
       ▼                          ▼                          ▼
 Application Pods           Kubernetes Nodes              GPU Nodes
       │                          │                          │
       │ /metrics                 │ kubelet/cAdvisor          │ DCGM Exporter
       │                          │                          │ /metrics
       ▼                          │ /metrics/cadvisor         │
 Application Metrics              ▼                          ▼
       │                     Container Metrics             GPU Metrics
       │                          │                          │
       └──────────────────────────┼──────────────────────────┘
                                  ▼
                             Prometheus
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
                Local TSDB    Alert Rules    remote_write
                    │             │             │
                    │             ▼             ▼
                    │        Alertmanager    AMP/Mimir/
                    │             │          Thanos/Cortex
                    │        ┌────┼────┐
                    │        ▼    ▼    ▼
                    │      Email Slack PagerDuty
                    │
                    └─────────────┬─────────────
                                  ▼
                               Grafana
```

## The key sentences

1. **Prometheus normally pulls metrics from `/metrics`.**
2. **cAdvisor provides container/Pod resource metrics through kubelet.**
3. **cAdvisor is not a database; Prometheus stores the time series.**
4. **`/metrics/cadvisor` is node-specific, not a combined endpoint for all nodes** —
   and DCGM Exporter follows the same node-scoped pattern for GPU metrics.
5. **Application `/metrics` is different from cAdvisor metrics** — resource usage vs.
   what the application is actually doing.
6. **Kubernetes service discovery automatically finds changing Pods**, so target lists
   never need manual updates as a Deployment scales.
7. **Prometheus Adapter is service discovery in reverse** — it exposes Prometheus
   metrics *to* Kubernetes (for HPA), rather than helping Prometheus find targets.
8. **Prometheus decides when an alert fires; Alertmanager decides how and where it's
   delivered** — two separate jobs, two separate components.
9. **Prometheus TSDB stores metrics locally; PVC/PV/EBS provides persistent storage.**
10. **`remote_write` forwards metrics to scalable external backends such as AMP or
    Mimir.**
11. **Grafana visualizes and queries the metrics; it is normally not the primary
    metrics store.**

## Related

- [`tools/prometheus/README.md`](tools/prometheus/README.md) and
  [`tools/cadvisor/README.md`](tools/cadvisor/README.md) — the reference write-ups for
  these two tools individually (deployment specifics, alternatives, a real
  `container` label gotcha found running cAdvisor live).
- [`tools/kube-state-metrics/README.md`](tools/kube-state-metrics/README.md) — the other
  "metrics with zero app instrumentation" source this doc doesn't cover: cAdvisor
  answers *how much resource*, kube-state-metrics answers *what Kubernetes object
  state*.
- [`observability-gpu-monitoring-dcgm-triton.md`](observability-gpu-monitoring-dcgm-triton.md) —
  the DCGM/GPU material §9 only summarizes: deployment modes, the `dcgmi` CLI,
  `nvidia-smi` vs. DCGM, and how Triton fits alongside GPU monitoring.
- [`observability-on-eks.md`](observability-on-eks.md) — where Prometheus/cAdvisor fit
  into the full EKS observability landscape (logs, traces, alerting included).
- [`../../k8s_observability/metrics-stack/`](../../k8s_observability/metrics-stack/) —
  this mental model, running: a `kube-prometheus-stack` install with a real
  scraped `/metrics` endpoint and cAdvisor/kube-state-metrics-backed Grafana panels,
  verified live against this repo's own `minikube` cluster.
- [`../../manual_notes/gpu-cluster-monitoring-lab.md`](../../manual_notes/gpu-cluster-monitoring-lab.md) —
  §9's DCGM Exporter pipeline, as a real hands-on lab: DaemonSet, `ServiceMonitor`,
  `PrometheusRule` alerts (§24's Alertmanager material, applied), and a
  troubleshooting checklist.
- [`../../manual_notes/Observability in AI Infrastructure.md`](../../manual_notes/Observability%20in%20AI%20Infrastructure.md) —
  §24's alerting material only sketches Alertmanager's mechanics; Part 7 there covers
  alert *design* in depth (thresholds, actionability, routing, avoiding alert
  fatigue).
