# Observability in AI Infrastructure

Seven-part note set, each part a self-contained topic that builds on the ones before
it: why AI systems need monitoring at all → GPU-level telemetry (DCGM) → cluster-wide
metrics (Prometheus) → visualizing them (Grafana) → following one request across
services (OpenTelemetry tracing) → turning all of the above into something that pages
a human (alerting). Kept in the original slide-note shape (short headers, terse
bullets) — enriched so each bullet explains *why*, not just *what*, since a bullet
alone ("Non-determinism") means nothing to someone seeing it for the first time.

1. [Why Monitoring AI Systems Matters](#part-1--why-monitoring-ai-systems-matters)
2. [GPU Monitoring with DCGM](#part-2--gpu-monitoring-with-dcgm)
3. [DCGM vs. nvidia-smi](#part-3--dcgm-vs-nvidia-smi)
4. [Metrics Collection with Prometheus](#part-4--metrics-collection-with-prometheus)
5. [Visualization Dashboards with Grafana](#part-5--visualization-dashboards-with-grafana)
6. [Tracing AI Requests with OpenTelemetry](#part-6--tracing-ai-requests-with-opentelemetry)
7. [Building Alerts for AI System Failures](#part-7--building-alerts-for-ai-system-failures)

---

## Part 1 — Why Monitoring AI Systems Matters

**Ensuring reliability, performance, and trust in production AI.**

### The monitoring mindset

**AI systems are not traditional apps.** A traditional web service either answers a
request correctly or throws a visible error — a 500, a stack trace, a failed health
check. An AI system can answer *every* request successfully (HTTP 200, valid-looking
output) while being quietly, progressively wrong. A recommendation model can keep
serving recommendations while its accuracy erodes for weeks; nothing crashes, nothing
alerts, and the first signal anyone gets is a business metric (conversion rate, fraud
catch rate) drifting downward with no obvious cause. That's the core reason AI
monitoring is its own discipline rather than "the same observability as any other
service": **the failure mode itself is different — silent and gradual, not loud and
sudden.**

> **Real-world example:** Zillow's "Zillow Offers" home-buying business used an
> algorithmic pricing model (a "Zestimate"-derived valuation) to make cash offers on
> homes at scale. Through 2021 the model kept confidently producing valuations — no
> crashes, no error responses — while systematically overpaying as the housing market
> shifted faster than the model adapted. By the time the mispricing was obvious in the
> business results rather than in a dashboard, Zillow had absorbed roughly half a
> billion dollars in inventory write-downs and shut the entire home-buying division
> down, cutting a quarter of the company's workforce. This is the exact failure mode
> described above: a model that never once "errored," and a very real, very late
> discovery via the P&L instead of via monitoring.

- **Visibility into black-box models** — A deployed model is, from the outside, a
  function you can't read the source of: input in, prediction out, no visibility into
  *why* it produced that prediction. Monitoring is how you get any signal at all about
  what's happening inside that function over time, since you can't just read the code
  and reason about correctness the way you would for a deterministic service.
- **Detect issues early** — The alternative to monitoring isn't "no problems," it's
  "problems discovered by users, or by a regulator, instead of by you." Drift, bias,
  and silent accuracy loss are all things that are cheap to catch with a dashboard and
  expensive to discover from a support ticket or a compliance audit.

### Why AI needs special monitoring

| Property | What it means | Why it matters for monitoring |
|---|---|---|
| **Non-determinism** | The same input can produce a different output across two runs (sampling temperature, floating-point non-associativity across hardware, model updates). | You can't rely on "same input → same output" as a correctness check the way you would for a pure function — you need statistical monitoring (distributions, drift) instead of exact-match testing. |
| **Data dependency** | Model output quality is a direct function of input quality — there's no equivalent of input validation catching a malformed request before it "breaks" anything. | A silent change in upstream data (a schema change, a sensor recalibration, a new user segment) degrades predictions with no error thrown anywhere — you only see it in the data itself. |
| **Model drift** | The world the model was trained on keeps changing after training stops — user behavior shifts, fraud patterns evolve, prices move. | Accuracy at deployment time is not accuracy six months later. A model that was correct is not guaranteed to *stay* correct, unlike a piece of business logic that stays correct until someone edits it. |
| **Infrastructure sensitivity** | GPU/memory contention, queue depth, and batching directly shape latency and throughput in ways CPU-bound services rarely see. | A model can be numerically correct and still be operationally failing — timing out, queueing, or getting evicted — for reasons that have nothing to do with the model itself. |

### Dimensions to monitor

Four layers, each answering a different question — and each one blind to what the
others catch:

- **Infrastructure metrics** — *"Is the hardware healthy?"* CPU/GPU utilization,
  memory consumption, network throughput. Necessary but not sufficient: a GPU can be
  running at 100% utilization while the model on it is producing garbage.
- **Model performance** — *"Is the model still good at its job?"* Accuracy, F1 score,
  perplexity, drift-detection metrics. This is the layer infrastructure metrics can't
  see — a perfectly healthy GPU tells you nothing about whether the model it's running
  has drifted.
- **Operational metrics** — *"Is the serving layer behaving?"* Latency (p95/p99),
  request throughput, error/failure rates. This is where you'd catch a queue backing
  up or a dependency timing out — problems in *serving* the model, distinct from
  problems *in* the model.
- **Business KPIs** — *"Does any of this actually matter to the business?"* Conversion
  rate, fraud-detection accuracy, customer satisfaction. The layer that answers "so
  what" — a model can be technically healthy on every metric above and still be
  costing the business money if it's making bad business-relevant decisions.

The reason to track all four rather than picking one: each layer can be green while
another is on fire. A model with perfect infrastructure metrics and perfect
operational metrics can still be silently wrong (model-performance layer), and a model
that's still statistically accurate can still be hurting the business if the world
changed around what "accurate" should mean (business layer).

### Failure modes without monitoring

What actually happens when none of the above is being watched:

- **Silent performance drops** — Accuracy degrades gradually rather than all at once,
  so there's no single moment that looks like an incident. By the time it's obvious
  (users complaining, KPIs down), the model has likely been degraded for a while —
  the cost compounds with every day undetected.
- **Infrastructure bottlenecks** — Everything looks fine at normal load, then the
  system falls over at peak load (a traffic spike, a batch job overlapping with live
  traffic) with no warning, because nothing was tracking utilization trends that would
  have shown the capacity ceiling approaching.
- **Data pipeline errors** — **Garbage in, garbage out.** If nothing is watching the
  *input* distribution, a corrupted or malformed upstream feed produces confidently
  wrong predictions with no error anywhere in the stack — the model isn't broken, the
  data feeding it is, and only input monitoring would catch that distinction.
- **Compliance violations** — Bias or fairness problems that go undetected in
  production aren't just a quality issue — in regulated domains (lending, hiring,
  healthcare) they're a legal and financial liability, and "we didn't know" is not a
  defense once it's found by a regulator instead of by your own monitoring.

> **Real-world example:** Amazon built an internal experimental recruiting model that
> scored resumes, trained on ten years of the company's own past hiring decisions.
> Because those historical decisions skewed male (reflecting the tech industry's
> existing gender imbalance, not any label the model was told about directly), it
> learned to penalize resumes containing words like "women's" (as in "women's chess
> club captain") and downgraded graduates of two all-women's colleges. Amazon's own
> engineers reportedly found and fixed specific instances of this, but couldn't be
> confident the model wasn't finding other, subtler proxies for gender — and scrapped
> the project in 2018 once it was clear no amount of patching would fully resolve it.
> No regulator caught this one first; Amazon's own team did, during internal review —
> but only years after the model had already been used, which is exactly the
> "undetected until reviewed" gap fairness monitoring in production is meant to close.

**Without monitoring, none of these fail loudly — they fail quietly, and by the time
they're visible without monitoring, they've usually already cascaded into a bigger
problem than they started as.**

### Monitoring across the lifecycle

Different questions matter at different stages — a metric that's essential during
training may be irrelevant post-deployment, and vice versa:

1. **Training** — Loss curves and convergence (is the model actually learning, or
   stuck/diverging?), resource utilization (is the training job using the GPUs it was
   allocated, or wasting money idling?), reproducibility checks (would re-running this
   produce the same model, or did something non-deterministic slip in?).
2. **Deployment** — Endpoint health and availability (is it up?), latency profiles
   under load (is it fast enough *under realistic traffic*, not just in a benchmark?),
   auto-scaling performance (does it actually scale in time, or does it lag behind a
   traffic spike?).
3. **Post-deployment** — Concept drift detection (has the relationship between inputs
   and correct outputs changed since training?), bias and fairness metrics (is the
   model treating population segments consistently over time, not just at launch?),
   real-world accuracy tracking (does live performance match what training/validation
   predicted it would be?).
4. **Continuous learning** — Feedback-loop capture (are real outcomes being fed back
   in to know if predictions were right?), automated retraining triggers (does drift
   crossing a threshold actually *do* something, or just sit in a dashboard?),
   performance-improvement tracking (is each retrain actually better, or just
   different?).

   > **Real-world example:** Microsoft's Tay chatbot (2016) learned continuously from
   > its Twitter conversations by design — every reply was training signal. There was
   > no monitoring on the *content* of what it was learning, and no rate limit or
   > review step between "users feed it something" and "it repeats that pattern
   > publicly." Coordinated users fed it hateful and inflammatory phrasing, and Tay was
   > posting racist and inflammatory tweets within about 16 hours, forcing Microsoft to
   > take it offline the same day. The infrastructure functioned exactly as designed
   > (a genuinely continuous-learning loop) — what was missing was any monitoring on
   > *what* it was learning, which is the whole point of pairing "automated retraining
   > triggers" with content/output review rather than treating "the loop runs" as
   > sufficient on its own.

**Each phase needs monitoring built for the questions specific to that phase** — a
training-time loss curve and a production drift score are both "AI monitoring," but
neither substitutes for the other.

### Tools & ecosystem

A quick map of which tool answers which layer — covered in depth in the parts that
follow:

| Layer | Tools | What they're for |
|---|---|---|
| **Infrastructure** | Prometheus, Grafana, DCGM | Hardware health, resource usage, GPU-specific telemetry. |
| **Model operations** | MLflow, Weights & Biases, EvidentlyAI | Experiment tracking, model lineage, and detecting drift once a model is in production. |
| **Observability** | OpenTelemetry, ELK stack, Datadog | Collecting and correlating traces, logs, and metrics across a distributed system. |
| **Business layer** | Custom dashboards | Purpose-built to connect technical metrics (latency, drift) to business outcomes (revenue, churn) — usually not off-the-shelf, since the KPIs are specific to the business. |

### Best practices

- **Define clear SLOs.** Set explicit targets for latency, accuracy, and uptime rather
  than monitoring "in general" — e.g. **p99 prediction latency < 200ms**. A number
  with no target is a chart to look at; a number with a target is something you can
  alert on and be held accountable to.
- **Monitor distributions, not averages.** Track p50/p95/p99, not just the mean — an
  average can look perfectly healthy while 5% of users are experiencing multi-second
  latency, because the slow tail is exactly what an average is mathematically designed
  to hide.
- **Combine signal types.** Correlate infrastructure, model, and business metrics
  together rather than watching them in isolation — the useful question is usually
  "did the GPU saturation at 2pm correlate with the latency spike and the conversion
  drop," not any one of those three facts alone.
- **Build alerts and playbooks, not just dashboards.** A dashboard nobody is paged
  from when it goes red is not monitoring, it's wallpaper. Pairing an alert with a
  clear response procedure is what actually reduces mean time to resolution (MTTR) —
  see [Part 7](#part-7--building-alerts-for-ai-system-failures).

### Key takeaways

- **Monitoring is not optional.** It's core infrastructure for AI reliability,
  performance, and trust — not a nice-to-have layered on afterward.
- **Coverage has to be comprehensive.** Infrastructure, model, operational, and
  business layers each catch failures the others are blind to.
- **It protects and it optimizes.** Safeguards user trust, supports compliance, and
  (via utilization/drift tracking) helps control the cost of expensive compute.

**Continuous monitoring is the foundation of MLOps maturity** — everything in the rest
of this document is one piece of building that foundation.

---

## Part 2 — GPU Monitoring with DCGM

**Deep visibility into NVIDIA GPU health and performance.**

### What is DCGM?

**DCGM (Data Center GPU Manager)** is NVIDIA's toolkit for continuous, low-level GPU
telemetry and management — the layer that exists specifically because GPUs need
monitoring that goes deeper than what general infrastructure tools (which mostly
understand CPU/memory/disk) are built for. It provides:

- Detailed health, utilization, and error metrics — not just "is it busy" but *why*
  it's busy or idle, and whether it's degrading.
- Integration with existing monitoring stacks (Prometheus, Kubernetes, Slurm) rather
  than requiring a bespoke GPU-only monitoring pipeline.
- Deployment patterns designed for enterprise/data-center scale, not just a single
  workstation.

**Integrates natively with Prometheus, Kubernetes, Slurm, and DCGM Exporter.**

### Why use DCGM?

- **GPUs are the bottleneck.** In AI infrastructure, GPUs are simultaneously the most
  expensive resource and the most likely thing to be the actual constraint on
  throughput — which makes visibility into them disproportionately valuable compared
  to any other single component.
- **CPU-style monitoring is insufficient.** Traditional infrastructure monitoring
  (built around CPU/memory/disk) has no concept of SM occupancy, tensor-core usage, or
  NVLink health — it can report a node as "healthy" while the GPU work running on it
  is badly degraded.
- **Comprehensive detection.** DCGM specifically identifies utilization inefficiency,
  memory errors, thermal throttling, and process-level GPU usage — the specific
  failure modes generic monitoring wasn't built to see.

**Bottom line:** without GPU-specific monitoring, AI workloads can silently
underperform or fail on hardware you're paying for by the hour — the waste is
invisible until something forces you to look for it.

### Key metrics exposed

- **Utilization** — GPU core percentage, memory utilization, SM (Streaming
  Multiprocessor) occupancy. High core utilization alone doesn't prove the GPU is
  doing useful work efficiently — pairing it with memory-bandwidth metrics is what
  distinguishes "compute-bound and busy" from "stalled waiting on memory but still
  showing utilization."
- **Memory** — used vs. free memory, bandwidth throughput, memory-controller
  utilization. This is where you'd catch a workload about to OOM, or a kernel that's
  memory-bandwidth-bound rather than compute-bound.
- **Power & thermals** — wattage consumption, throttling events, fan speed and
  temperature. A GPU throttling due to heat looks like reduced performance with no
  error anywhere — these metrics are the only way to see *why* throughput dropped.
- **Errors & process stats** — ECC memory errors, PCIe/NVLink connectivity issues,
  PID-to-GPU resource mapping. This is the "is the hardware itself degrading" layer —
  catching a GPU heading toward failure before it actually fails mid-job.

### DCGM deployment modes

Four different ways to consume the same underlying telemetry, each suited to a
different operational need:

- **Embedded mode** — the DCGM library is linked directly into an application (C or
  Python bindings), for teams building a fully custom monitoring solution rather than
  using DCGM's own tooling.
- **Standalone mode** — the `dcgmi` command-line interface, for a system administrator
  running on-demand diagnostics and checks interactively.
- **DCGM Exporter** — a Prometheus-compatible `/metrics` HTTP endpoint, for wiring
  DCGM into an *existing* Prometheus/Grafana monitoring stack rather than standing up
  something GPU-specific and separate.
- **Kubernetes integration** — used by NVIDIA's Kubernetes device plugin for GPU
  allocation and health reporting, so the scheduler itself can see GPU health, not
  just an external dashboard.

**Bottom line:** development-time debugging, ad-hoc admin checks, and production
cluster monitoring are different problems, and DCGM ships a different mode of access
built for each rather than forcing one interface to serve all three.

### CLI examples with `dcgmi`

```bash
# List all GPUs on the system
dcgmi discovery

# Get utilization and memory usage for GPU 0
dcgmi stats --gpu 0

# Run short diagnostics (level 1)
dcgmi diag -r 1

# Enable a health-monitoring group
dcgmi health --set 1
```

The CLI is for quick checks, diagnostics, and scripting — the same telemetry DCGM
Exporter surfaces to Prometheus, but available directly on a box without needing the
full monitoring stack running.

**Pro tip:** run these in CI/CD, as a pre-flight check that validates GPU health
*before* an expensive training or inference job starts — catching a bad GPU before it
wastes hours of compute is far cheaper than catching it after.

### DCGM Exporter for Prometheus

DCGM Exporter is the bridge between DCGM's GPU-specific telemetry and a general
Prometheus/Grafana stack that otherwise has no idea GPUs exist:

- Runs as a **DaemonSet** — one pod per GPU node, so every node's GPUs are covered
  automatically as the cluster scales, with no manual per-node setup.
- Exposes a standard `/metrics` HTTP endpoint that Prometheus scrapes exactly like it
  would scrape any other exporter.
- Ships metrics under **consistent, standardized names**, so a Prometheus query
  written against one cluster's GPU metrics works unmodified against another.

Example metrics exposed:

```text
DCGM_FI_DEV_GPU_UTIL       # GPU utilization percentage
DCGM_FI_DEV_MEM_COPY_UTIL  # Memory controller activity
DCGM_FI_DEV_POWER_USAGE    # Power consumption, in watts
```

### Kubernetes integration

```text
GPU Node
  │
  ├── NVIDIA GPU Operator ── deploys DCGM Exporter DaemonSet automatically
  │
  └── DCGM Exporter DaemonSet ── /metrics, labeled by node + GPU index + pod
             │
             ▼
        Prometheus ── scrapes every GPU node's exporter
             │
             ▼
          Grafana
```

- **NVIDIA GPU Operator** — includes DCGM Exporter by default and deploys it
  automatically on every GPU node, so "install GPU support on this cluster" already
  gets you GPU monitoring, rather than that being a separate step someone has to
  remember.
- **Auto-labeling** — metrics come pre-labeled by node name, GPU index, and pod
  identifier, which is what makes it possible to answer "which specific GPU, on which
  node, is this problem on" directly from a PromQL query instead of manually
  cross-referencing.
- **Scaling integration** — these metrics can feed a Horizontal Pod Autoscaler or a
  custom autoscaler, so scaling decisions can be *GPU-aware* (scale on GPU saturation)
  rather than only CPU/memory-aware, which is the wrong signal for a GPU-bound
  workload.

**Bottom line:** this integration is what turns "GPU metrics exist" into "the cluster
can actually act on GPU metrics" — scheduling, scaling, and alerting all become
possible once the data is in the same system as everything else.

### Health monitoring features

DCGM's health monitoring is *proactive*, not just descriptive — it's built to catch
problems before they cause a failed job, not just report metrics after the fact:

- Predefined health-check groups for different monitoring scenarios (so you don't
  have to hand-pick which checks matter).
- Detection of **XID errors** — the specific class of critical GPU exceptions NVIDIA
  hardware/driver reports when something has gone seriously wrong.
- Monitoring of thermal thresholds and clock-throttling events, catching performance
  degradation that has a physical cause, not a software one.
- Integration with schedulers to **automatically quarantine failing GPUs** — pulling a
  degrading GPU out of the scheduling pool before it silently corrupts or slows down
  the next job placed on it.

This matters most for long-running training jobs specifically: a training run that
takes days can waste all of that time and cost on hardware that started failing
partway through, if nothing was watching for it and pulling the bad GPU out of
rotation.

> **Real-world example:** Meta AI's public logbook for training OPT-175B (a
> 175-billion-parameter language model, 2022) is a widely cited, unusually candid
> account of exactly this problem at scale — the training run spanned roughly two
> months on hundreds of GPUs, and the logbook documents repeated hardware failures
> (GPUs dropping out, NCCL/interconnect errors, nodes needing to be manually rebooted
> or swapped) requiring the job to be restarted from checkpoints dozens of times over
> the run. It's one of the clearest public illustrations of why "continuously monitor
> and auto-quarantine failing GPUs" isn't a theoretical best practice — at
> multi-week, multi-hundred-GPU scale, some hardware *will* fail mid-run, and the only
> question is whether monitoring catches it in minutes or the job silently degrades
> (or fully stalls) for hours before a human notices.

### Visualization & dashboards

NVIDIA ships ready-to-use Grafana dashboards for DCGM metrics, so the common case
(look at GPU health) doesn't require building a dashboard from scratch:

- Per-GPU visualization of utilization, power, and temperature — the "one GPU, right
  now" view.
- Cluster-wide views to spot underused or failing GPUs across the whole fleet — the
  "where's the problem, across everything" view.
- Custom alerting for temperature spikes and ECC errors, so these dashboards aren't
  purely passive — they can page someone.
- Historical trend analysis for capacity planning — using past utilization to decide
  whether to buy more GPUs or better-schedule the ones already owned.

### Best practices

1. **Deploy DCGM Exporter in every GPU cluster.** Treat it as a standard component,
   not an optional add-on — inconsistent coverage means some clusters are blind spots
   by default.
2. **Track utilization efficiency.** An idle or underused GPU is expensive idle
   capacity — dashboards built specifically to surface this make reallocation an
   active decision instead of something nobody notices.
3. **Implement proactive alerting.** Alert on ECC errors, overheating, and NVLink
   issues *before* they cause a workload failure, not after — the whole point of
   health-monitoring data is catching problems early enough to act.
4. **Use metrics for capacity planning.** Historical utilization data turns "should we
   buy more GPUs" from a guess into a decision backed by actual usage trends.

### Key takeaways

- **DCGM is the gold standard for GPU observability** — node-level and cluster-level
  visibility, through multiple deployment modes suited to different needs.
- **It enables proactive management** — alerts, scaling, and health monitoring that
  prevent costly failures rather than just reporting them afterward.
- **It's essential infrastructure for AI workloads at scale** — making it possible to
  actually operate and optimize GPU resources rather than running them blind.

---

## Part 3 — DCGM vs. nvidia-smi

**`nvidia-smi` = inspect/control one GPU right now.**
**DCGM = continuously monitor, diagnose, manage, and expose GPU health/telemetry at
scale.**

These two tools are easy to conflate because they're both "the NVIDIA GPU tool," but
they solve different problems — one is a point-in-time inspection command, the other
is an infrastructure-level monitoring framework.

### 1. `nvidia-smi`

`nvidia-smi` is NVIDIA's command-line interface for system-management functionality —
the tool you reach for when you want a direct, immediate answer about one GPU.

```bash
nvidia-smi
```

```text
GPU  Name        Temp   Power   Memory-Usage    GPU-Util
0    A100        65C    250W    12000MiB/40GB   87%
```

Useful for: GPU model, driver/CUDA version, GPU utilization, VRAM utilization,
temperature, power, running GPU processes, ECC information, clocks, and basic
troubleshooting.

You can also query specific fields directly, which is what you'd actually use in a
script rather than parsing the human-readable table above:

```bash
nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used --format=csv
```

**Think of it this way:** `nvidia-smi` is like logging into a server and asking, *"What
is happening with my GPU right now?"* — a snapshot, on demand, of one machine.

### 2. DCGM

**DCGM = NVIDIA Data Center GPU Manager** — a much larger monitoring/management
framework than `nvidia-smi`. NVIDIA describes it as providing tools and libraries for
observing, managing, validating, and integrating data-center GPUs — the word
"data-center" is the key difference: it's built for fleets, not single machines.

DCGM can provide: continuous GPU telemetry, health monitoring, ECC/error monitoring,
GPU diagnostics, NVLink/PCIe topology information, process/job statistics, profiling
metrics, policy/alert mechanisms, configuration management, APIs in C/Python/Go, and
Kubernetes integration through **DCGM Exporter**.

For example, where `nvidia-smi` gives you one snapshot per invocation:

```bash
dcgmi dmon
```

streams metrics continuously, rather than you repeatedly re-running `nvidia-smi` and
comparing outputs by hand.

### The important architecture difference

Both tools ultimately read from the same underlying data — NVIDIA's driver and the
**NVML** (NVIDIA Management Library) beneath it — but they build very different things
on top of that shared foundation:

```text
                    NVIDIA Driver
                         │
                         ▼
                        NVML
                    ┌────┴────┐
                    │         │
                    ▼         ▼
              nvidia-smi     DCGM
                               │
                     ┌─────────┼──────────┐
                     │         │          │
                  dcgmi    DCGM API    DCGM Exporter
                                              │
                                              ▼
                                         Prometheus
                                              │
                                              ▼
                                           Grafana
```

`nvidia-smi` reads NVML directly and stops there — it's a leaf, not a platform.
DCGM's core library (`libdcgm.so`) also sits on top of NVML (optionally through the
NVIDIA Host Engine), but then exposes *multiple* consumption paths on top of itself —
a CLI, an API, and an exporter that feeds an entire downstream monitoring stack.

**So DCGM isn't simply "a bigger `nvidia-smi`."** It's an infrastructure-level GPU
management/monitoring framework that `nvidia-smi` is not designed to be — the two
aren't really alternatives to each other so much as different layers.

### Why DCGM matters for Kubernetes/EKS

This is the distinction that actually matters operationally. Suppose you have:

```text
EKS Cluster
├── Node 1 ── GPU 0, GPU 1
├── Node 2 ── GPU 0, GPU 1
└── Node 3 ── GPU 0, GPU 1
```

The `nvidia-smi` way to check all of this is:

```bash
ssh node1 && nvidia-smi
ssh node2 && nvidia-smi
ssh node3 && nvidia-smi
```

— which does not scale past a handful of nodes, requires SSH access to every node,
and gives you no historical data, no alerting, and no single place to look.

The DCGM way replaces per-node manual SSH with a pipeline that scales with the
cluster automatically:

```text
GPU Nodes
   │
   ▼
  DCGM              (runs on every node)
   │
   ▼
DCGM Exporter       (exposes /metrics per node)
   │
   ▼
Prometheus          (scrapes every node's exporter)
   │
   ▼
 Grafana             (one dashboard, whole fleet)
```

From that single pipeline you can monitor, across the entire fleet at once: GPU
utilization, GPU memory utilization, GPU temperature, GPU power, ECC errors,
PCIe/NVLink activity, SM activity, and tensor-core activity. DCGM's profiling metrics
specifically are designed for **continuous cluster-wide telemetry at relatively low
overhead** — meaning "leave this running all the time," not "run occasionally because
it's expensive."

### One useful interview distinction

| Capability | `nvidia-smi` | DCGM |
|---|---|---|
| Basic GPU information | ✅ | ✅ |
| GPU utilization | ✅ | ✅ |
| Memory usage | ✅ | ✅ |
| Temperature | ✅ | ✅ |
| Running processes | ✅ | ✅ |
| Continuous monitoring | Basic | **Excellent** |
| Health checks | Limited | **Strong** |
| Diagnostics | Limited | **Advanced** |
| Profiling metrics | Limited | **Yes** |
| GPU topology (NVLink/PCIe) | Limited | **Yes** |
| API | CLI-oriented | **C / Python / Go** |
| Kubernetes monitoring | Not designed for it | **DCGM Exporter** |
| Prometheus integration | Not directly | **Yes** |
| Multi-GPU / data-center management | Basic | **Designed for it** |

DCGM's health/diagnostic capabilities go beyond passive monitoring — it can actively
check PCIe/NVLink connectivity, memory, hardware, power/thermal behavior, and
software-integration issues, rather than only reporting numbers and leaving the
interpretation to a human.

### So remember this

- **`nvidia-smi`:** *"Tell me what my GPU is doing."*
- **DCGM:** *"Continuously monitor, diagnose, manage, and expose my GPUs to the
  infrastructure."*

And for an **EKS + Prometheus + Grafana** environment specifically, the mental model
to hold onto is:

```text
NVIDIA GPU
   │
   ▼
  DCGM
   │
   ▼
DCGM Exporter
   │
   ▼
Prometheus
   │
   ▼
 Grafana
```

That pipeline — not individual `nvidia-smi` flags — is what's actually relevant to an
MLOps/infra interview or to designing a real system: the flags are trivia, the
architecture is the thing you'll actually be asked to reason about.

---

## Part 4 — Metrics Collection with Prometheus

### The foundation of observability for AI infrastructure

A guide for DevOps/SRE and ML infrastructure engineers working with Kubernetes and AI
workloads — this is the layer everything in Parts 2–3 (DCGM/GPU metrics) ultimately
feeds into.

### What is Prometheus?

- **Metrics monitoring system** — an open-source time-series database with a
  **pull-based** model: Prometheus itself reaches out and scrapes HTTP endpoints at
  `/metrics` on a schedule, rather than waiting for applications to push data to it.
  This inverts the usual "app pushes logs/metrics somewhere" pattern, and it's a
  deliberate design choice, not an incidental detail — see "Prometheus's pull model"
  below for why it matters.
- **PromQL query language** — a purpose-built query language for time series,
  supporting aggregation, filtering, and the kind of math (rates, quantiles) that raw
  counters and gauges can't answer on their own.
- **Cloud-native architecture** — built with Kubernetes service discovery and dynamic
  configuration in mind, so it's designed to track a fleet where pods come and go
  constantly, not a fixed list of servers.

### Why Prometheus for AI workloads?

- **Unified observability** — infrastructure, GPU, model, and pipeline metrics all
  live in one system with one query language, instead of a different tool per layer
  that you'd have to cross-reference by hand.
- **High-cardinality support** — labels let you track metrics per-model, per-node,
  per-GPU (`gpu="0"`, `model="bert"`) so you can pinpoint *which* instance is the
  problem, not just that "something, somewhere" is degraded.
- **Rich ecosystem integration** — works directly with DCGM (GPU metrics), Triton
  (model-serving metrics), MLflow, and Kubernetes — the exact stack this document
  covers, not a generic metrics tool that happens to also work here.
- **Actionable insights** — the same metrics power alerts, dashboards, and
  autoscaling decisions, so instrumenting once pays off across all three uses rather
  than needing separate systems for each.

### Core Prometheus concepts

- **Metrics** — numeric measurements collected at regular intervals, forming a
  time series (a value, with a timestamp, repeated over time).
- **Labels** — key-value pairs that add dimensions to a metric, e.g. `gpu="0"`,
  `model="bert"`. Labels are what turn one generic metric name into many distinct,
  independently-queryable time series — see the cardinality warning further down for
  the cost of that power.
- **PromQL** — the query language for expressing aggregations, filters, and
  transformations over those time series.
- **Scrape targets** — anything exposing a `/metrics` HTTP endpoint that Prometheus is
  configured to pull from on an interval.

### Understanding metric types

Four fundamentally different shapes of data — using the wrong type for a given metric
produces numbers that are technically present but semantically meaningless:

- **Counter** — cumulative, only ever increases (or resets to zero on a restart).
  **Example:** `total_inferences_served` — a running count of inference requests
  handled. You never read a counter's raw value for a rate; you apply `rate()` to it
  (see PromQL examples below) to get "requests per second," which is almost always
  the actually-useful question.
- **Gauge** — a value that can go up or down, representing the current state.
  **Example:** `gpu_memory_used_bytes` — real-time memory consumption, read directly
  as "what is it right now."
- **Histogram** — distribution data, bucketed by value ranges, computed server-side.
  **Example:** `inference_duration_seconds_bucket` — the data behind latency
  percentile queries (`histogram_quantile()`, shown below).
- **Summary** — similar to a histogram, but quantiles are pre-computed **client-side**
  by the application before Prometheus ever scrapes them. **Example:**
  `request_duration_quantiles` for p50/p95/p99. The tradeoff versus a histogram:
  summaries can't be aggregated *across* instances after the fact (each instance's
  quantile is already fixed), while histograms can be — which is why histograms are
  the more common choice for anything you'll want to aggregate cluster-wide later.

### Exporters for AI infrastructure

Exporters exist because most systems don't speak Prometheus's `/metrics` format
natively — an exporter is the translation layer between "some system's native metrics"
and "something Prometheus can scrape":

- **Node Exporter** — system-level metrics: CPU, memory, disk, network, for the host
  machine itself.
- **DCGM Exporter** — NVIDIA GPU metrics: utilization, memory usage, temperature,
  power (covered in depth in [Part 2](#part-2--gpu-monitoring-with-dcgm)).
- **Triton Server** — model-serving metrics: inference requests, latency, queue time,
  cache hit rate — Triton exposes these natively, no separate exporter needed.
- **Custom exporters** — application-specific KPIs from FastAPI, TorchServe, or any
  other custom ML service that isn't covered by an off-the-shelf exporter.

### Scrape configuration example

```yaml
# prometheus.yml
scrape_configs:
  - job_name: "gpu-metrics"
    static_configs:
      - targets: ["node1:9400", "node2:9400"]

  - job_name: "triton"
    static_configs:
      - targets: ["triton-svc:8002"]
```

Prometheus scrapes each listed target on an interval, pulling in every metric that
target's `/metrics` endpoint exposes. Each `job_name` becomes a `job` label attached to
every metric it produces — which is what lets a later query filter or group by "which
job did this metric come from" (`sum(...) by (job)`, for example). Scrape intervals
are configurable; **15 or 30 seconds** is a typical default, balancing how quickly you
notice a change against how much load scraping itself puts on targets and storage.

*(In production Kubernetes, `static_configs` with hardcoded targets like this is the
exception rather than the rule — see [Part 1's Kubernetes service discovery
note](#part-1--why-monitoring-ai-systems-matters) and the `k8s/k8s_observability/`
charts in this repo for the actual mechanism: Prometheus discovering pods dynamically
via `ServiceMonitor`/`PodMonitor` rather than a static target list that would need
manual edits every time something scales.)*

### PromQL in action

```promql
# GPU utilization, averaged across the whole cluster
avg(DCGM_FI_DEV_GPU_UTIL)
```
Averages the GPU-utilization gauge across every GPU Prometheus is scraping — one
number for "how busy is the fleet, overall."

```promql
# Inference queries-per-second, broken out per model
rate(nv_inference_count[1m]) by (model)
```
`rate()` turns the *cumulative* counter `nv_inference_count` into a per-second rate
over a trailing 1-minute window; `by (model)` keeps that rate broken out per model
label instead of collapsing everything into one number — this is the query you'd
actually use to answer "which model is getting the most traffic right now."

```promql
# p95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```
`histogram_quantile()` computes a percentile from histogram bucket data — this is the
server-side counterpart to what a Summary type computes client-side (see "Understanding
metric types" above). `0.95` is what makes this specifically the *95th* percentile,
i.e. "the latency 95% of requests were faster than."

### Metrics storage & retention

Balancing "fast to query recent data" against "keep enough history to be useful":

- **Local TSDB** — Prometheus's own high-performance local storage, optimized for
  recent data (days to weeks) with efficient compression. This is what's actually
  fast to query, and it's what most dashboards hit.
- **Remote storage** — Cortex, Thanos, or Mimir for long-term retention, historical
  analysis, and compliance needs local TSDB isn't designed to serve at scale (see
  Part 1's mention of `remote_write` — this is exactly that mechanism).
- **Model performance history** — retaining metrics specifically to track drift,
  degradation, and performance change *over time*, not just "what's the value right
  now" — this is a retention decision driven by the model-monitoring use case, not a
  generic infra one.

**Bottom line:** for AI workloads specifically, historical metrics aren't just
"nice to review later" — they're what lets you establish a baseline (what does
"normal" performance look like) that later alerting and drift detection actually
depend on. Without history, "is this drifting" has no reference point to drift away
*from*.

### Best practices

- **Meaningful labels** — tag metrics with model name, version, and owning team, so a
  metric can be filtered down to exactly the slice that matters and traced back to
  whoever's responsible for it.
- **Percentile monitoring** — track p50/p95/p99 distributions, not just averages, for
  the same reason as Part 1: averages hide the tail, and the tail is where users
  actually suffer.
- **Cardinality management** — keep high-cardinality labels (like raw user IDs) out of
  metrics; every unique label *combination* creates a brand-new time series, so
  careless labeling can silently multiply Prometheus's storage and query load by
  orders of magnitude.
- **Security controls** — put authentication, authorization, and TLS in front of
  `/metrics` endpoints; an unauthenticated metrics endpoint can leak operational
  detail (traffic patterns, internal hostnames, model names) to anyone who finds it.

⚠️ **Performance alert:** watch for **cardinality explosion** — using too many label
combinations. Every unique combination of label values is a *new, separate* time
series Prometheus has to store and index; a label like "user ID" or "request ID" on a
metric can turn one logical metric into millions of actual time series, which is a
common way to accidentally make Prometheus itself the thing that falls over.

> **Real-world example:** this is one of the most commonly reported real production
> incidents among teams running Prometheus at scale — enough so that Grafana Labs
> (whose own commercial product exists partly to solve this) has written extensively
> about it in their public engineering content. The typical story is mundane and
> repeats across companies: someone adds a well-intentioned label — a user ID, a raw
> URL path with an embedded ID, a Kubernetes pod name that churns constantly — to an
> existing metric. Nothing about the change looks dangerous in code review. Over the
> following days or weeks, memory usage on the Prometheus server climbs steadily as
> the number of distinct time series grows into the millions, until Prometheus
> itself starts OOMing, falls behind on scraping, or stops responding to queries —
> taking down the very observability stack that was supposed to catch problems like
> this. The fix is almost always the same one this document already recommends:
> remove or aggregate away the high-cardinality label before ingestion, not after the
> outage.

### Key takeaways

- **Comprehensive observability** — Prometheus is the backbone unifying metrics across
  every layer covered so far.
- **Multi-layer visibility** — infrastructure, GPU, model, and application metrics, in
  one system with one query language.
- **Powerful querying** — PromQL supports the aggregation and math (rates, quantiles)
  that raw counters/gauges alone can't answer.
- **Ecosystem integration** — works directly with Grafana, Alertmanager, and
  Kubernetes for a complete stack, rather than needing glue code to connect them.

**Next steps:** implement exporters for your specific AI stack, then build dashboards
around the key indicators — which is exactly [Part 5](#part-5--visualization-dashboards-with-grafana).

### Triton — brief summary

**NVIDIA Triton Inference Server** is software for serving ML models, particularly
when efficient GPU inference matters:

```text
Client → Triton → Model → NVIDIA GPU → Response
```

It supports multiple frameworks, request batching, concurrent requests, multiple model
instances, and both GPU and CPU inference — one serving layer, many model types, rather
than a different server per framework.

**Important:** Triton is **not a managed AWS service** — you deploy and operate it
yourself (on EKS, EC2, or any Kubernetes cluster), though it can also run *inside* a
managed service like SageMaker as the container SageMaker invokes.

**Main alternatives:**

| Alternative | Best for |
|---|---|
| **vLLM** | LLM inference |
| **Hugging Face TGI** | LLMs / Hugging Face models |
| **TorchServe** | PyTorch models |
| **TensorFlow Serving** | TensorFlow models |
| **KServe** | Kubernetes-native model serving/platform |
| **Ray Serve** | Distributed Python/ML serving |
| **BentoML** | Custom Python ML APIs |
| **SageMaker** | AWS-managed inference, including GPU inference |

**The easiest way to remember it:**

```text
Triton    → general-purpose GPU model serving
vLLM      → LLM serving specifically
TGI       → LLM / Hugging Face serving
KServe    → Kubernetes-native inference platform
SageMaker → AWS-managed inference
```

And don't confuse serving with monitoring — they answer completely different
questions about completely different things:

```text
Triton      → SERVES the model
DCGM        → MONITORS the GPU
nvidia-smi  → INSPECTS the GPU
```

---

## Part 5 — Visualization Dashboards with Grafana

### Turning metrics into insights for AI systems

A comprehensive approach to monitoring and visualizing AI infrastructure metrics for
faster troubleshooting and better performance insight.

### What is Grafana?

Grafana is an open-source **analytics and visualization platform** — it turns raw
metrics (from Prometheus and elsewhere) into dashboards a human can actually read at a
glance, rather than requiring someone to run PromQL queries by hand every time they
want to check on something.

It connects to multiple data sources at once — **Prometheus, Loki, Elastic,
CloudWatch**, and many others — which is what makes it a natural *centralized*
visualization layer: one tool, many backends, instead of a different UI per data
source.

### Why Grafana for AI infrastructure?

- **Unified visualization** — GPU health, latency, and drift metrics in one place,
  instead of switching between separate tools per signal.
- **Faster anomaly detection** — a visual pattern in a chart (a spike, a slow climb) is
  often far faster to spot than the same anomaly buried in raw metric values or logs.
- **Cross-team visibility** — ML engineers, SREs, and business stakeholders can look
  at the *same* underlying data through dashboards built for each audience's actual
  questions, rather than each team needing its own separate source of truth.
- **Integrated alerting** — connects to Alertmanager, PagerDuty, and Slack, so a
  dashboard isn't purely passive — the same thresholds that render a red panel can
  also page someone (see [Part 7](#part-7--building-alerts-for-ai-system-failures)).

### Core building blocks

1. **Data sources** — connections to Prometheus (metrics), Loki (logs), Tempo
   (traces), and others — Grafana itself stores no data, it only queries and renders.
2. **Panels** — individual visualizations: graphs, gauges, heatmaps, tables, stat
   panels — each suited to a different shape of data (see "Visualization types"
   below).
3. **Dashboards** — collections of panels organized around one use case or domain
   (e.g. "GPU health," "inference performance").
4. **Alerts** — thresholds and notification channels defined on top of the same
   queries the panels already use.

### Example dashboards for AI

- **GPU utilization** — per-node and cluster-wide usage; temperature, power, ECC
  errors; memory allocation tracking.
- **Inference performance** — QPS, p95/p99 latency, error rates; request queue depth;
  batch-size optimization metrics.
- **Data drift & quality** — input distribution histograms; feature-drift scores over
  time; data-quality metrics.
- **Business KPIs** — conversion rate by model version; fraud-detection accuracy;
  SLA compliance tracking.

### Prometheus + Grafana setup

1. **Add Prometheus as a data source** — configure the connection URL and
   authentication in Grafana's data-source settings.
2. **Create PromQL queries** — build the query that feeds each panel.
3. **Configure auto-refresh** — set a refresh interval appropriate to how fast the
   underlying data actually changes, so the dashboard stays current without
   re-querying far more often than the data updates.

Example PromQL queries, as they'd actually appear in a panel:

```promql
# Request rate by model
rate(nv_inference_count[5m]) by (model)
```

```promql
# p95 latency by instance
histogram_quantile(0.95,
  sum(rate(inference_latency_bucket[5m])) by (le, instance))
```

(`le` here is the histogram's "less than or equal" bucket-boundary label —
`histogram_quantile()` needs it present in the `sum by (...)` clause to correctly
reconstruct the distribution before computing the percentile; dropping it from the
`by` clause is a common way to get a subtly wrong number instead of an error.)

### Visualization types

- **Time-series graphs** — best for latency trends, GPU-utilization patterns, and
  request volume *over time* — anything where the shape of the trend matters, not
  just the current value.
- **Single-stat gauges** — best for at-a-glance KPIs: SLA compliance, error rate — a
  single number you want to be able to read without interpreting a chart.
- **Heatmaps** — visualize latency *distributions* across GPUs, surfacing hotspots a
  single averaged line would hide.
- **Tables** — per-model metrics with versions, useful for comparing many instances
  side by side rather than overlaying them on one chart.

**Bottom line:** pick the visualization that matches the *shape* of the question —
"how did this change over time" wants a time series, "what's the distribution" wants a
heatmap, "compare N things" wants a table. Complex metrics often genuinely need more
than one visualization type to tell the full story.

### Dashboards in Kubernetes

- **Deployment options** — run Grafana via a **Helm chart** or an **Operator** for
  Kubernetes-native lifecycle management; import NVIDIA's GPU + Triton community
  dashboard templates rather than building from scratch; configure persistent storage
  so dashboard definitions survive a pod restart.
- **Organization** — integrate with Kubernetes **RBAC** for team-based access control;
  use **folders** to group dashboards by domain (infrastructure/ML/business); use
  namespace-based segregation for multi-tenant clusters.
- **Pro tip:** the **kube-prometheus-stack** Helm chart deploys Prometheus, Grafana,
  and a set of default dashboards together, pre-wired with sane defaults — this is
  exactly the chart [`k8s/k8s_observability/practice/metrics-stack/`](../k8s/k8s_observability/practice/metrics-stack/)
  in this repo wraps, tuned for a local `minikube` cluster and verified live rather
  than left as an abstract description here.

```text
GPU Nodes and applications
   │
   ▼
Deploy Prometheus + Grafana via Helm
   │
   ▼
Grafana pods  ◄────  Prometheus pods
   │
   ▼
  Kubernetes cluster, fully monitored
```

### Advanced features

- **Annotations** — mark events (deployments, retraining, outages) directly on a
  time-series graph. **Example:** automatically add an annotation via API the moment a
  new model version deploys, so a subsequent metric shift has an obvious, visible
  explanation on the same chart instead of requiring someone to remember the deploy
  time separately.
- **Variables** — dropdown selectors that dynamically filter a dashboard by cluster,
  model, or namespace. **Example:** one dashboard template that works unmodified
  across dev/staging/prod, instead of maintaining three near-identical copies.
- **Drilldowns** — click from a high-level cluster view straight into detailed
  pod-level metrics. **Example:** jump from "this model overall" to "this specific
  instance" in one click instead of re-navigating from scratch.
- **Alerting 2.0** — unified alerts across multiple data sources with routing logic.
  **Example:** one alert correlating a Prometheus metric *and* a log pattern from
  Loki, instead of two separate, uncorrelated alerts a human has to connect manually.

### Best practices

1. **Audience-focused design** — separate dashboards for infra teams, ML engineers,
   and business stakeholders, each at the level of detail *that audience* actually
   needs — a business stakeholder doesn't need SM-occupancy panels, and an ML
   engineer doesn't need a revenue chart.
2. **Prioritize key metrics** — p95/p99 latency, GPU saturation, queue depth, and
   error rate as the primary health indicators — the small set of numbers that, if
   they're all green, most other things are probably fine too.
3. **Embrace templating** — variables and template functions to build reusable
   dashboards that work across environments and models, rather than one dashboard per
   model that all drift out of sync with each other.
4. **Implement GitOps** — store dashboard JSON in version control and provision it via
   CI/CD, so a dashboard's history is auditable and a bad change can be reverted like
   any other code change, instead of living only as undocumented state inside
   Grafana's own database.

⚠️ **Common pitfall:** too many near-duplicate dashboards with overlapping metrics.
Consolidate related visualizations and use variables to filter within *one* dashboard
rather than hand-duplicating a dashboard per model/cluster/team.

### Key takeaways

- **Visualization power** — turns raw Prometheus metrics into actionable insight
  through dashboards, rather than requiring everyone to know PromQL.
- **A complete toolkit** — dashboards, alerts, and collaboration in one platform.
- **An essential component** — a must-have piece of any real AI observability stack,
  not an optional add-on once Prometheus is already running.

**Next steps:** start from the NVIDIA GPU dashboard template and customize it for your
own infrastructure, rather than starting from a blank dashboard.

---

## Part 6 — Tracing AI Requests with OpenTelemetry

**End-to-end visibility across distributed AI systems.**

### What is OpenTelemetry?

An open-source **observability framework** under the Cloud Native Computing Foundation
(CNCF):

- **Unified standard** — collects traces, metrics, and logs in one standardized
  format, so you're not stitching together three incompatible per-signal tools.
- **Ecosystem integration** — works with Prometheus, Grafana, Jaeger, Datadog, and
  other backends — OpenTelemetry itself is the *instrumentation and collection* layer,
  not the storage/visualization layer, which is why it plugs into tools this document
  has already covered rather than replacing them.
- **Multi-language support** — SDKs for Python, Go, Java, C++, and more, so
  instrumentation isn't limited to a single-language stack.

### Why tracing matters for AI

- **Multi-layer complexity** — a single AI request typically crosses several
  services: `API → preprocessing → model inference → database → postprocessing`. Any
  one of those layers can be where the actual problem is.
- **Hidden failure points** — performance issues and failures often live deep inside
  that chain, somewhere traditional single-service debugging (check this one
  service's logs) can't reach on its own.
- **Root-cause visibility** — tracing gives you the *entire* request's path across
  every service boundary in one place, which is what actually enables root-cause
  analysis instead of guessing which service to look at first.
- **Tail-latency detection** — essential for debugging p95/p99 outliers specifically:
  an average-latency metric tells you nothing about *which stage* in the pipeline is
  responsible for the slow 1% of requests; a trace shows you exactly that.

> **Real-world example:** this exact pain point is *why* one of the most widely used
> tracing backends exists at all. Uber's engineering team, running a large and
> rapidly growing microservices architecture, found that debugging cross-service
> latency by manually correlating logs from dozens of independently-deployed services
> didn't scale past a certain point — no single service's logs could show the whole
> picture of one request's journey. They built an internal distributed tracing system
> to solve it, open-sourced it in 2017 as **Jaeger**, and it's since become a CNCF
> graduated project used well beyond Uber. The origin story is the argument for
> tracing in one sentence: at enough services, "check the logs" stops being a
> debugging strategy and becomes a research project, unless something is already
> stitching the whole request together for you.

### Core tracing concepts

- **Trace** — the complete journey of one request across every service it touched,
  start to finish.
- **Span** — one individual operation *within* a trace (e.g. "model inference," "data
  preprocessing") — a trace is made of many spans, nested or sequential.
- **Context propagation** — the mechanism (a trace ID, passed along with the request)
  that lets every service the request touches attach its spans to the *same* trace,
  rather than each service unknowingly starting an unrelated trace of its own.
- **Attributes & events** — metadata attached to a span: model name, version, input
  size, execution time — the detail that turns "this span was slow" into "this span
  was slow *for this specific model version, on this input size*."

A trace contains multiple spans, each capturing its own timing and context — the
combination is what lets you see not just *that* a request was slow, but *where in
the pipeline* it was slow.

### AI pipeline example trace

```text
Request/FastAPI ── initial request handling & preprocessing
      │
      ▼
Triton Server ── model inference execution
      │
      ▼
Feature Store ── data lookup and retrieval
      │
      ▼
Postprocessing ── result transformation
      │
      ▼
Response ── final output delivered
```

Each stage above is one span within the trace. The complete trace reveals the latency
breakdown across every one of these services — which is precisely what lets you say
"the feature store lookup is 80% of this request's latency" instead of just "this
request was slow," with no way to say why.

### Instrumenting AI services

**Python SDK for AI frameworks** — adding tracing to FastAPI, Flask, TorchServe, and
other serving frameworks is often close to one line, via auto-instrumentation:

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# One line to instrument the entire FastAPI app
FastAPIInstrumentor().instrument_app(app)
```

This automatically instruments HTTP endpoints, database calls, and external
dependencies — the common cross-cutting concerns — without hand-writing a span for
every single function call.

**Key implementation steps:**

1. Install the OpenTelemetry SDK and the instrumentation packages for your framework.
2. Configure a trace exporter pointed at your chosen backend (Jaeger, Tempo, etc.).
3. Add auto-instrumentation for the framework(s) you're using.
4. Create *custom* spans for model-specific operations auto-instrumentation can't see
   on its own (e.g. "tokenization," "batch assembly").
5. Attach trace IDs to log lines, so a log entry can be correlated back to the exact
   trace/request it came from — without this step, traces and logs stay two separate,
   uncorrelated systems even when both are collecting data about the same request.

### Exporters & backends

- **Open source** — **Jaeger** and **Tempo** are full open-source tracing backends
  with their own visualization/query layers.
- **Unified observability** — **Grafana + Tempo + Loki** combine traces, metrics, and
  logs in one UI, so you can pivot between all three signals for the same request
  without switching tools.
- **Cloud-native** — **AWS X-Ray, GCP Trace, Azure Monitor** are managed alternatives,
  trading self-hosted control for less operational overhead.

All of these backends speak **OTLP** (the OpenTelemetry Protocol) — a standardized
wire format for sending telemetry, which is what lets you swap backends later without
re-instrumenting every service: the instrumentation talks OTLP, not to any specific
vendor's proprietary format.

### Tracing GPU & model layers

Custom instrumentation for the ML-specific pieces auto-instrumentation doesn't cover:

- **Model execution spans** — spans that specifically capture *inference time* for
  individual model components, with Triton's own custom metrics linked into the
  OpenTelemetry span so the two data sources aren't siloed from each other.
- **Rich context attributes** — attach model version, batch size, GPU ID, and tensor
  shapes as span attributes — the detail that lets you later ask "was this slow trace
  specifically the large-batch-size requests, or the small ones?"
- **Infrastructure correlation** — link spans back to Prometheus metrics, so an
  application-level trace can be correlated with the infrastructure state (GPU
  utilization, memory) at the exact moment it ran — connecting "this request was slow"
  to "because the GPU it landed on was saturated at that moment."

### Sampling strategies

Tracing *every single request* is expensive at real production volume — sampling is
how you trade completeness for cost, and different strategies make that trade
differently:

| Strategy | Rate | Pros | Cons |
|---|---|---|---|
| **Always-on** | 100% | Complete visibility — every request traced | Expensive at scale — storage and overhead grow linearly with traffic |
| **Probabilistic** | 1–10% | Predictable, bounded overhead | May simply miss the specific problematic requests you'd actually want to see |
| **Tail-based** | p95+ (slow/error cases) | Captures exactly the problematic requests | Requires a *dynamic* sampling implementation — the decision to keep a trace can only be made after seeing how it turned out |

Choose based on traffic volume, infrastructure capacity, and observability budget — a
common pattern is starting with high (or 100%) sampling in development, where volume
is low and completeness is cheap, then reducing it in production where volume makes
100% sampling expensive.

### Benefits for AI Ops

- **Real-time inference debugging** — identify and resolve latency spikes in
  production model serving as they happen, not after a post-mortem.
- **Infrastructure bottleneck detection** — pinpoint *which* dependency (feature
  store, database) is actually the slow one, instead of guessing.
- **Data-pipeline correlation** — trace a drift issue back to a specific upstream
  data-source's latency or quality problem, connecting a model-layer symptom to an
  infrastructure-layer cause.
- **Accelerated incident response** — cut MTTR with precise root-cause visibility
  spanning every service in the request path, instead of manually correlating logs
  across services by hand.

> Teams implementing comprehensive tracing have reported meaningfully lower mean time
> to resolution for complex, multi-service AI pipeline issues — root-cause work that
> used to mean manually correlating logs across five services becomes "look at the one
> trace."

### Best practices

- **End-to-end propagation** — always propagate trace context across *every* service
  boundary, including batch jobs and async workers — a trace that silently breaks at
  one hop stops being end-to-end at exactly that point, and the gap is often invisible
  until you go looking for it.
- **Consistent tagging** — standardized span attributes for model, version,
  environment, and team, so traces are filterable/comparable across services rather
  than each service inventing its own attribute names.
- **Strategic sampling** — balance visibility against resource consumption and storage
  cost, per the tradeoffs in the sampling table above.
- **Integrated observability** — connect traces with logs and metrics rather than
  treating them as three separate systems that happen to describe the same request.

**Maintain a consistent naming convention for spans** across every service — this is
what keeps visualization clear and queries simple in the tracing backend; inconsistent
naming is what turns "search for this operation across services" into "search for five
different names that all mean the same thing."

### Key takeaways

- **OpenTelemetry provides the standard framework** for instrumenting modern AI
  pipelines — one instrumentation layer, many possible backends.
- **It delivers end-to-end visibility** across distributed infrastructure components
  that no single service's logs could show on their own.
- **It's critical for debugging tail-latency issues** and pinpointing bottlenecks a
  latency average would hide entirely.
- **It integrates with Prometheus and Grafana** for a genuinely complete observability
  stack — metrics, logs, and traces together, not three separate tools.

**Start small:** instrument the critical paths first, and expand coverage
incrementally — full end-to-end tracing on day one is rarely realistic, and partial
coverage on the paths that matter most is still far better than none.

---

## Part 7 — Building Alerts for AI System Failures

### From reactive firefighting to proactive reliability

A practical guide for SREs, ML engineers, and engineering managers responsible for
keeping AI systems reliable.

### Why alerts matter

AI systems fail in **subtle and silent ways** — the theme running through this entire
document — without the obvious crashes traditional systems produce. Early detection,
via alerting rather than a human staring at dashboards all day, prevents:

- **Customer-facing outages** — catching a problem before users experience it, not
  after they've already noticed and complained.
- **Model drift going unnoticed** — preventing gradual degradation from silently
  running for weeks before anyone looks at the right dashboard.
- **Expensive infrastructure waste** — catching wasted or idle expensive compute
  before it accumulates into a large, avoidable cloud bill.

**Alerts are the bridge between monitoring and action.** A dashboard is monitoring; an
alert is what turns monitoring into someone actually doing something about it.

> **Real-world example:** Knight Capital Group (2012) is the canonical case study for
> "monitoring/alerting that could have stopped this, but didn't." A deployment
> mistake left old test code active on one of eight production trading servers. Once
> markets opened, that server began executing a runaway sequence of unintended
> trades. There was no automated circuit breaker watching for "this system's behavior
> just changed drastically" and firing before real damage accumulated — the problem
> was ultimately caught by humans noticing unusual trading activity, by which point it
> was already too late: **$440 million lost in about 45 minutes**, and the firm was
> sold off within days. It's not an AI-model example specifically, but it's the
> sharpest illustration in this entire document of the point Part 1 opened with:
> a system can be technically "up" — no crash, no outage — while doing something
> silently, rapidly, catastrophically wrong, and the only thing standing between that
> and a business-ending loss is whether something was watching closely enough, with a
> low enough time-to-detection, to catch it in *minutes* rather than after the fact.

### Types of failures to alert on

Alerting needs coverage at every layer from Part 1 — a gap at any one layer is a class
of failure that will never page anyone:

1. **Infrastructure** — GPU out-of-memory errors, thermal throttling events, node
   crashes or restarts, network connectivity issues.
2. **Operational** — high p95/p99 latency spikes, error-rate increases, request
   throughput anomalies, batch-job failures.
3. **Model-level** — accuracy/precision drops, feature-drift signals, bias or fairness
   issues, prediction-confidence changes.
4. **Business-level** — KPI degradation (e.g. CTR), rising fraud rate, customer-churn
   signals, revenue-impact indicators.

### Anatomy of a good alert

An alert is more than a threshold — a threshold with no context or next step is just
noise with a trigger attached:

- **Signal** — the specific metric, log pattern, or event that fires the alert.
  **Example:** `model_inference_latency_p95 > threshold`.
- **Threshold** — **static** (a fixed value, e.g. >80% GPU for 10 minutes) or
  **dynamic** (SLO-based — 2× baseline, or derived from historical patterns rather
  than a hand-picked constant).
- **Actionability** — clear next steps for whoever is on call, ideally linked directly
  to a runbook rather than left for them to figure out from scratch under pressure.
- **Context** — model, version, cluster, and team labels, plus any relevant recent
  changes — everything needed to start investigating *without* first having to go
  looking for that context elsewhere.

```text
Alert signal → Threshold → Context → Action steps
```

> "An alert that doesn't lead to action is just noise."

### Prometheus alerting example

```yaml
# alert.rules.yml
groups:
  - name: ai-infra
    rules:
      - alert: HighGPULatency
        expr: histogram_quantile(0.95,
          rate(inference_latency_bucket[5m])) > 200
        for: 5m
        labels:
          severity: critical
          team: ml-platform
          component: inference
        annotations:
          summary: "High GPU inference latency"
          description: "p95 >200ms on {{ $labels.model }} in {{ $labels.cluster }}"
          runbook: "https://docs.example.com/runbooks/high-latency"
```

`expr` is the same p95-latency PromQL pattern from [Part 4](#part-4--metrics-collection-with-prometheus),
now wired into an alert rather than just a dashboard panel. `for: 5m` requires the
condition to stay true for five full minutes before firing — a deliberate guard
against paging someone over a single noisy scrape rather than a real, sustained
problem. The `labels` block is what Alertmanager uses to *route* the alert (see
below); the `annotations` block is the human-readable context — note the
`{{ $labels.model }}` templating, which pulls the actual model name into the alert
text rather than leaving the responder to go look it up themselves.

💡 **Pro tip:** use templating in alert descriptions to include the specific instance,
service, and threshold that triggered — the goal is that the alert *itself* already
answers "what, where, and how bad," with no extra lookup required just to understand
the page.

### Routing alerts

**Alertmanager** handles deduplication and intelligent routing on top of raw alert
firing:

```text
Alert fires (threshold breach)
        │
        ▼
Processing — deduplication, grouping, inhibition
        │
        ▼
Routing — sent to the right channel, by severity and team
```

Severity levels determine urgency and destination:

- **Critical** — immediate action required → **PagerDuty**.
- **Warning** — attention needed, but not immediately → **Slack**.
- **Info** — awareness only, no action expected → **Email**.

### Avoiding alert fatigue

An alerting system that pages too often trains people to ignore it — which defeats
the entire purpose of alerting in the first place:

- **Focus on SLOs, not every metric.** Alert on service-level objectives that actually
  matter to users, not on every metric fluctuation that happens to cross some
  arbitrary line.
- **Use multi-window thresholds.** Combine short-term sensitivity (5m) with
  longer-term confirmation (1h) — this is what filters out transient noise while
  still catching genuinely sustained problems quickly.
- **Group related alerts.** Consolidate multiple related symptoms of one incident into
  a single notification, instead of paging the same person ten times for ten symptoms
  of one root cause.
- **Regular alert hygiene.** Review alert patterns monthly, and tune or remove the
  ones that are consistently noisy — an alert nobody acts on twice in a row is a
  candidate for deletion or retuning, not something to leave firing indefinitely.

> **Real-world example:** the "multi-window threshold" technique above (short-term
> sensitivity plus longer-term confirmation) is directly drawn from Google's SRE
> practice — Google's publicly published *Site Reliability Engineering* book devotes
> significant material specifically to this problem, describing how naive
> single-threshold alerting on error-budget burn rate produces exactly the alert
> fatigue this section warns about: either too sensitive (paging on every brief blip)
> or too slow (missing a real fast-burning incident until the budget is already
> gone). Their solution — multi-window, multi-burn-rate alerting, combining a
> short window for fast detection with a longer window to confirm the problem is
> real and sustained — is precisely the technique generalized here, and it's worth
> knowing this isn't an arbitrary rule of thumb: it's a documented answer to a
> problem one of the largest SRE organizations in the world hit and wrote about
> specifically because ad-hoc thresholds kept failing in one of these two directions.

⚠️ **Teams receiving more than 5–8 actionable alerts per day will start to ignore
them** — past that volume, the signal-to-noise ratio degrades faster than any
individual alert's importance, and the whole system stops functioning as intended.

### AI-specific alerting patterns

- **Model drift detection** — alert when feature distributions or prediction patterns
  deviate significantly from an established baseline.
- **GPU underutilization** — flag expensive idle resources that could be reallocated
  or scaled down, turning waste into something someone actually sees and acts on.
- **Data pipeline stalls** — detect when no new training data has arrived within the
  expected timeframe, catching a stalled upstream pipeline before it shows up as a
  stale model later.
- **Shadow model disagreement** — alert when a canary or shadow model's predictions
  diverge significantly from the production model's — an early signal something
  changed, before the shadow model is ever promoted to production.

Roughly, higher-level alerts (business-layer) tend to require more investigation time
to diagnose than lower-level ones (infrastructure), but they also tend to represent
costlier failures if left unresolved — which is part of why coverage across *all*
layers matters: cheap-to-diagnose infra alerts catch problems early and cheaply,
before they escalate into expensive-to-diagnose business-layer symptoms.

### Incident playbooks

Every alert should link to a **runbook** — step-by-step troubleshooting instructions,
so the response doesn't depend on the specific person paged already knowing the
system by heart.

**Example: high inference latency playbook**

1. **Check HPA scaling status** — is the autoscaler functioning, and are pods actually
   scaling in response to load as expected?
2. **Inspect GPU utilization with DCGM** — check for thermal throttling, memory
   pressure, or other GPU-level bottlenecks (tying directly back into
   [Part 2](#part-2--gpu-monitoring-with-dcgm)).
3. **Analyze request patterns** — look for unusual input sizes, batch sizes, or
   traffic patterns that might explain the slowdown.
4. **Roll back the latest model, if needed** — revert to the previous stable version
   if the issue persists and no infrastructure cause is found.

> Well-documented playbooks meaningfully reduce mean time to resolution — the value
> isn't just having a plan, it's that the *first* responder, even one unfamiliar with
> this specific system, can follow it without needing to page someone more senior just
> to know where to start.

💡 **Tip:** update playbooks after every incident with what was actually learned —
a runbook that never gets revised stops matching how the system actually fails over
time.

### Best practices

- **Define multi-layer coverage.** Alerts should exist at all four levels from
  earlier in this section — infrastructure, operational, model, and business — not
  concentrated in just one layer while the others stay blind.
- **Use SLO-based thresholds.** Base thresholds on customer-experience goals, not
  arbitrary numbers or technical guesses that happen to feel reasonable.
- **Establish clear on-call practices.** Document who responds to what, when, and how
  escalation works, including follow-the-sun rotation for globally distributed teams.
- **Test before production.** Validate new alerts in staging first, to catch false
  positives and routing mistakes before they page someone for real.

### Key takeaways

- **Turn monitoring into action.** Alerts are what convert passive monitoring data
  into signals that actually drive a response.
- **Cover every failure mode.** Infrastructure, operational, model, and business
  layers all need alerting coverage — a gap in any one is a class of failure that
  will never page anyone.
- **Fight alert fatigue actively.** Prioritize SLO-based, actionable alerts, and
  regularly prune the noisy ones rather than letting them accumulate.
- **Enable rapid recovery.** Pairing alerts with detailed runbooks is what actually
  decreases MTTR — the alert gets someone's attention, the runbook is what lets them
  act on it quickly.
