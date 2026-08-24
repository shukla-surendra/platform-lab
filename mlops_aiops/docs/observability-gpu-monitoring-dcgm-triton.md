# Prometheus, DCGM, Triton & Scalable Metrics — Summary

## 1. The basic GPU monitoring pipeline

A common Kubernetes/EKS GPU monitoring architecture looks like:

```text
NVIDIA GPU
    │
    ▼
   DCGM
    │
    ▼
DCGM Exporter
    │
    │ exposes /metrics
    ▼
Prometheus
    │
    ▼
Prometheus TSDB
    │
    ▼
Grafana
```

### Roles

- **DCGM** — NVIDIA Data Center GPU Manager. Collects/monitors GPU telemetry and health information.
- **DCGM Exporter** — exposes DCGM GPU metrics as a Prometheus-compatible HTTP `/metrics` endpoint.
- **Prometheus** — scrapes `/metrics`, stores the samples, and provides a query engine.
- **Grafana** — queries Prometheus (or another metrics backend) and visualizes the data.

---

# 2. `nvidia-smi` vs DCGM

## `nvidia-smi`

`nvidia-smi` is mainly a command-line tool for inspecting and managing NVIDIA GPUs.

Typical information:

- GPU model
- GPU utilization
- GPU memory usage
- Temperature
- Power
- Running GPU processes
- Clocks
- ECC information

Think:

> **`nvidia-smi` = inspect a GPU right now**

Example:

```bash
nvidia-smi
```

## DCGM

DCGM is a broader NVIDIA data-center GPU management and monitoring framework.

It provides:

- Continuous telemetry
- GPU health monitoring
- Diagnostics
- ECC/error information
- PCIe/NVLink information
- Profiling metrics
- APIs
- Kubernetes integration through DCGM Exporter

Think:

> **DCGM = continuously monitor, diagnose, and manage GPUs**

### Easy distinction

```text
nvidia-smi → inspect
DCGM       → monitor/manage
```

---

# 3. Triton Inference Server

NVIDIA Triton Inference Server is **software for serving ML models**.

It is not a physical server.

Conceptually:

```text
Client
  │
  │ inference request
  ▼
Triton
  │
  ▼
ML Model
  │
  ▼
NVIDIA GPU
  │
  ▼
Prediction
```

Triton can:

- Serve multiple models
- Support multiple ML frameworks
- Run inference on GPU or CPU
- Perform batching
- Handle concurrent requests
- Run multiple model instances
- Expose metrics

### Is Triton managed?

Triton itself is generally **client-managed software**.

You can run it on:

- AWS EC2
- AWS EKS
- Kubernetes
- Your own data center

You can also use Triton within managed platforms such as SageMaker.

### Important distinction

> **Triton = model-serving runtime**

It is not equivalent to an AWS managed service.

---

# 4. Alternatives to Triton

| Technology | Main use |
|---|---|
| **Triton** | General-purpose GPU model serving |
| **vLLM** | High-performance LLM serving |
| **Hugging Face TGI** | LLM / Hugging Face model serving |
| **TorchServe** | PyTorch model serving |
| **TensorFlow Serving** | TensorFlow model serving |
| **KServe** | Kubernetes-native inference platform |
| **Ray Serve** | Distributed Python/ML serving |
| **BentoML** | Custom Python ML APIs |
| **SageMaker** | AWS-managed model inference |

### Easy mental model

```text
Triton    → general GPU model serving
vLLM      → LLM serving
TGI       → LLM/Hugging Face serving
KServe    → Kubernetes inference platform
SageMaker → AWS-managed inference
```

---

# 5. Does SageMaker support GPU inference?

Yes.

SageMaker supports GPU-backed inference using GPU instance families such as G4, G5, G6 and P-series instances.

Conceptually:

```text
AWS
└── SageMaker Endpoint
      │
      └── GPU Instance
            │
            └── Model Container
                  │
                  └── NVIDIA GPU
```

### SageMaker vs Triton

| | SageMaker | Triton |
|---|---|---|
| Type | Managed ML platform/service | Inference server software |
| GPU inference | Yes | Yes |
| Infrastructure management | AWS manages much of it | You manage it |
| EKS-native | No | Yes |
| Model serving | Yes | Yes |
| Control | Lower | Higher |

They are not necessarily alternatives.

You can use:

```text
SageMaker
   │
   └── Triton container
        │
        └── NVIDIA GPU
```

So:

> **SageMaker = managed deployment/infrastructure layer**  
> **Triton = model-serving runtime**

---

# 6. Prometheus: Pull model

Prometheus normally **pulls/scrapes** metrics.

Suppose a pod exposes:

```text
http://my-pod:8080/metrics
```

Prometheus periodically performs:

```text
GET /metrics
```

Architecture:

```text
Pod
 │
 │ exposes /metrics
 ▼
Prometheus
 │
 │ scrape
 ▼
Prometheus TSDB
```

The pod does **not normally push metrics directly to Prometheus**.

### Pushgateway

There is a component called **Pushgateway**:

```text
Pod / Batch Job
      │
      │ push
      ▼
Pushgateway
      │
      │ Prometheus scrapes
      ▼
Prometheus
```

Pushgateway is mainly useful for short-lived/batch jobs, not the standard model for long-running services.

### Important terminology

Metrics are not the same as traces.

```text
Metrics → Prometheus
Logs    → Loki / OpenSearch / Elasticsearch etc.
Traces  → OpenTelemetry / Tempo / Jaeger etc.
```

---

# 7. DCGM Exporter exposes `/metrics`

Yes.

DCGM Exporter exposes an HTTP endpoint, commonly on port 9400:

```text
http://<dcgm-exporter>:9400/metrics
```

Prometheus scrapes it:

```text
Prometheus
    │
    │ GET /metrics
    ▼
DCGM Exporter
    │
    ▼
DCGM
    │
    ▼
NVIDIA GPU
```

The endpoint can contain metrics such as:

```text
DCGM_FI_DEV_GPU_UTIL 87
DCGM_FI_DEV_FB_USED 12345
DCGM_FI_DEV_GPU_TEMP 65
```

In Kubernetes, a Service can provide stable discovery:

```text
GPU Node
  │
  └── DCGM Exporter Pod
          │
          │ :9400/metrics
          ▼
       Kubernetes Service
          │
          ▼
       Prometheus
```

---

# 8. What is Prometheus TSDB?

TSDB means:

> **Time-Series Database**

Prometheus has its **own built-in TSDB**.

It does not require PostgreSQL, MySQL, InfluxDB, etc. by default.

Prometheus stores measurements along with timestamps.

Example:

```text
Metric              Time       Value
--------------------------------------
gpu_temperature     10:00:01   70
gpu_temperature     10:00:02   71
gpu_temperature     10:00:03   72
gpu_temperature     10:00:04   73
```

This is a time series.

Prometheus TSDB uses structures such as:

- TSDB blocks
- WAL (Write-Ahead Log)
- Index
- Compressed chunks

Conceptually:

```text
/prometheus
├── wal/
├── chunks_head/
├── block-1/
│   ├── chunks/
│   ├── index
│   └── meta.json
└── block-2/
    ├── chunks/
    └── index
```

---

# 9. Kubernetes: where does Prometheus store its data?

This distinction is important:

> **TSDB = how Prometheus stores metrics**  
> **PVC/PV/EBS = where the storage physically lives**

A production Kubernetes setup can look like:

```text
Prometheus Pod
      │
      │ mounted volume
      ▼
     PVC
      │
      ▼
     PV
      │
      ▼
    AWS EBS
```

The Prometheus TSDB files are stored on that mounted volume.

### Without persistent storage

```text
Prometheus Pod
      │
      ▼
Container filesystem
      │
      X
Pod deleted
      │
      ▼
Data may be lost
```

### With persistent storage

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
EBS
```

The metrics survive Pod recreation, assuming the persistent volume remains available.

---

# 10. Can Prometheus write to an external TSDB?

Yes.

Prometheus supports **remote_write**.

Instead of only:

```text
Prometheus
    │
    ▼
Local TSDB
```

you can have:

```text
Prometheus
   │
   ├── Local TSDB
   │
   └── remote_write
           │
           ▼
      External metrics backend
```

For example:

```yaml
remote_write:
  - url: <remote-write-endpoint>
```

The important point:

> `remote_write` sends **metrics**, not logs.

Prometheus can keep local data while also forwarding metrics to the remote backend.

---

# 11. Do we need a Prometheus server?

If you self-host Prometheus, yes, you need a Prometheus process/instance (or another compatible collector architecture) to scrape metrics.

In Kubernetes:

```text
EKS
│
├── Application Pods
├── DCGM Exporter
└── Prometheus
```

You are then responsible for operating the Prometheus deployment.

This includes considering:

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

However, Prometheus scaling is not simply:

```text
Prometheus Pod
      │
      ▼
HPA
      │
      ▼
10 Prometheus Pods
```

Larger environments commonly use architectures involving remote storage, Thanos, Mimir, or managed Prometheus services.

---

# 12. Amazon Managed Service for Prometheus (AMP)

AWS provides **Amazon Managed Service for Prometheus**.

The idea is:

```text
EKS
 │
 ├── DCGM Exporter
 │
 └── Prometheus / collector
          │
          │ remote_write
          ▼
        AMP
          │
          ▼
       Grafana
```

AWS manages the backend infrastructure.

You still need metric collection/scraping in your environment, but you don't have to operate the entire scalable Prometheus storage backend yourself.

### Self-hosted vs managed

Self-hosted:

```text
YOU
 │
 ├── Prometheus
 ├── Storage
 ├── Scaling
 ├── HA
 ├── Retention
 └── Upgrades
```

AMP:

```text
YOU
 │
 └── Collector / Prometheus
          │
          │ remote_write
          ▼
       AWS AMP
          │
          ▼
     Managed backend
```

---

# 13. What are Mimir, Thanos and Cortex?

These technologies address the problem:

> **"What happens when Prometheus needs large-scale, long-term, centralized metrics storage?"**

Imagine multiple clusters:

```text
Cluster 1 → Prometheus
Cluster 2 → Prometheus
Cluster 3 → Prometheus
Cluster 4 → Prometheus
```

You may want one centralized metrics system.

---

## Grafana Mimir

Mimir is a horizontally scalable, long-term, Prometheus-compatible metrics backend.

```text
Prometheus-1 ──┐
Prometheus-2 ──┼──► Mimir
Prometheus-3 ──┘
                  │
                  ▼
             Object Storage
```

Think:

> **Mimir = large centralized metrics backend for Prometheus**

It is designed for:

- Long-term storage
- Horizontal scaling
- High availability
- Multi-cluster metrics
- Prometheus-compatible querying

---

# 14. Thanos

Thanos extends Prometheus with capabilities such as:

- Long-term storage
- Global querying
- High availability
- Multiple Prometheus instances
- Object storage integration

Conceptually:

```text
Prometheus-1 ──┐
Prometheus-2 ──┼──► Thanos
Prometheus-3 ──┘      │
                      ▼
                     S3
```

A common architecture is:

```text
Prometheus
   │
   ├── Local TSDB
   │
   └── Thanos
          │
          ▼
         S3
```

---

# 15. Cortex

Cortex is another horizontally scalable, Prometheus-compatible metrics backend.

```text
Prometheus
    │
    ▼
 Cortex
    │
    ▼
Object Storage
```

Cortex was designed to solve the same broad class of problems:

- Scalable metrics storage
- High availability
- Multiple Prometheus instances
- Long-term storage

Mimir is derived from the Cortex project and is part of the Grafana ecosystem.

---

# 16. The big picture

Putting everything together:

```text
                         EKS
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
     Application      DCGM Exporter     Triton
       /metrics          /metrics       inference
          │               │
          └───────┬───────┘
                  │
                  ▼
             Prometheus
                  │
          ┌───────┴────────┐
          │                │
          ▼                ▼
      Local TSDB      remote_write
          │                │
          ▼                ▼
       PVC/EBS       Mimir / Thanos /
                     Cortex / AMP
                          │
                          ▼
                       Grafana
```

The responsibilities are:

```text
Triton
  → SERVES ML models

DCGM
  → MONITORS NVIDIA GPUs

DCGM Exporter
  → EXPOSES GPU metrics as /metrics

Prometheus
  → SCRAPES /metrics and QUERIES metrics

Prometheus TSDB
  → LOCALLY STORES time-series metrics

PVC / PV / EBS
  → PROVIDES PERSISTENT STORAGE for the TSDB

remote_write
  → FORWARDS metrics to another backend

Mimir / Thanos / Cortex
  → PROVIDE scalable/long-term Prometheus-compatible metrics storage

AMP
  → AWS-MANAGED Prometheus-compatible metrics backend

Grafana
  → VISUALIZES/QUERIES metrics
```

## The five sentences to remember

1. **Prometheus pulls metrics from `/metrics`; applications normally don't push directly to Prometheus.**
2. **DCGM Exporter exposes NVIDIA GPU metrics through `/metrics`.**
3. **Prometheus stores scraped metrics in its built-in TSDB, normally backed by a Kubernetes PVC/PV in production.**
4. **Prometheus can use `remote_write` to send metrics to a scalable external backend such as Mimir, Thanos-compatible architectures, Cortex, or AWS AMP.**
5. **Grafana is the visualization/query layer; it is not normally the place where Prometheus metrics are stored.**

## Related

- [`observability-prometheus-and-cadvisor.md`](observability-prometheus-and-cadvisor.md) —
  the general Prometheus/Kubernetes fundamentals this doc assumes (pull model, TSDB,
  `remote_write`, service discovery) without re-deriving them, scoped here to what's
  GPU-specific on top.
- [`tools/prometheus/README.md`](tools/prometheus/README.md) and
  [`tools/vllm/README.md`](tools/vllm/README.md) — reference write-ups for two of the
  named tools here (Prometheus itself, and vLLM as Triton's LLM-serving alternative).
- [`tools/nvidia-training-gpus/README.md`](tools/nvidia-training-gpus/README.md) — GPU
  hardware selection (T4/V100/L4/A100); this doc is about monitoring GPUs already
  chosen and running, not choosing them.
- [`../../fundamentals/gpu_infrastructure/phase6_production_operations/17_observability_for_gpu_fleets.md`](../../fundamentals/gpu_infrastructure/phase6_production_operations/17_observability_for_gpu_fleets.md) —
  picks up from this doc's DCGM Exporter → Prometheus pipeline with the actual
  GPU metric catalog (compute/memory-bandwidth/NVLink/ECC) and dashboard design,
  organized by which GPU failure mode each metric catches.
