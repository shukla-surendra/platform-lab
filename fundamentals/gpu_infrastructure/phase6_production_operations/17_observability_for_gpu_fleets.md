# Observability for GPU Fleets: The MONITOR Stage, in Detail

Part of [Phase 6 — Production Operations](../README.md#phase-6-production-operations).
Builds on [`15_gpu_fleet_lifecycle.md`](15_gpu_fleet_lifecycle.md)'s MONITOR stage and
[`04_cuda_ecosystem.md`](../phase2_gpu_fundamentals/04_cuda_ecosystem.md)'s introduction
of DCGM. This chapter assumes Prometheus/Grafana fundamentals are already solid from
[`platform-lab/mlops_aiops/docs/observability-prometheus-and-cadvisor.md`](../../../mlops_aiops/docs/observability-prometheus-and-cadvisor.md)
(pull model, TSDB, `remote_write`, Kubernetes service discovery) and
[`k8s_mlops/`](../../../k8s/k8s_mlops/) — it covers only the GPU-specific metric catalog and
dashboard design on top of that general stack, the same scoping this track applies to
Kubernetes in Phase 4. The DCGM Exporter → Prometheus pipeline mechanics specifically
(and how Triton/vLLM/KServe fit alongside GPU metrics) are covered in
[`observability-gpu-monitoring-dcgm-triton.md`](../../../mlops_aiops/docs/observability-gpu-monitoring-dcgm-triton.md) —
this chapter picks up from there with the actual metric catalog, not the pipeline.

## Clarify

Generic infrastructure observability (CPU, memory, request latency, error rate) is
already a solved, familiar problem in this workspace's existing build-outs. What's
GPU-specific, and genuinely new, is a metric catalog and set of dashboard patterns built
around the specific failure modes this entire track has surfaced — memory-bound vs.
compute-bound confusion, topology degradation, KV cache pressure, XID errors. This
chapter is that catalog, organized by which earlier chapter's failure mode each metric is
actually meant to catch.

## Core Concepts

### The metric catalog, organized by what it catches

```
Compute utilization
  DCGM_FI_DEV_GPU_UTIL          — SM utilization %
  DCGM_FI_PROF_SM_ACTIVE        — more precise SM-active fraction than
                                    the coarser utilization metric above

  Catches: nothing on its own — as established repeatedly across this
  track (03_gpu_architecture.md onward), high utilization alone does
  NOT rule out a memory-bound stall. This metric is only meaningful
  paired with the memory metrics below.

Memory bandwidth utilization
  DCGM_FI_PROF_DRAM_ACTIVE      — fraction of time HBM is actively
                                   being read/written

  Catches: exactly the failure this track has repeatedly warned about
  — a GPU showing high compute utilization while ACTUALLY stalled
  waiting on HBM reads is caught by comparing this metric against SM
  utilization together, not either alone. This is the concrete,
  queryable version of "check GPU utilization AND memory bandwidth
  together" from aws-production-architecture.md's monitoring section.

NVLink / interconnect throughput
  DCGM_FI_PROF_NVLINK_TX_BYTES / RX_BYTES

  Catches: the topology-degradation failure mode from
  05_nvlink_nvswitch_topology.md — a healthy topology should show
  NVLink throughput consistent with the workload's expected all-reduce
  volume; a degraded link shows persistently lower throughput than
  expected for the same workload, the ongoing/monitoring-time version
  of what nccl-tests checks at validation time.

ECC / ROW REMAP events
  DCGM_FI_DEV_ECC_DBE_VOL_TOTAL, DCGM_FI_DEV_ROW_REMAP_FAILURE

  Catches: exactly the XID/row-remapping signal from
  16_reliability_and_failure_management.md — DCGM exposes this as a
  scrapeable metric, not just a dmesg log line, which is what makes it
  alertable through the same Prometheus/Grafana stack as everything
  else, rather than requiring separate log-watching tooling.

Power / thermal
  DCGM_FI_DEV_POWER_USAGE, DCGM_FI_DEV_GPU_TEMP

  Catches: thermal throttling — a GPU running hot enough to
  automatically reduce its own clock speed to protect itself, which
  looks like an unexplained throughput regression unless power/thermal
  metrics are checked directly.

Application-level (from the serving engine, not DCGM)
  TTFT, TPOT, KV cache occupancy, queue depth — already named in
  aws-production-architecture.md and detailed in
  12_llm_performance_engineering.md — these come from the serving
  engine itself (vLLM etc.), not from DCGM, and need to be scraped and
  correlated ALONGSIDE the GPU-level metrics above, not treated as a
  separate, unrelated dashboard.
```

**The single organizing principle worth remembering over the specific metric names**:
every metric in this catalog exists to catch a *specific, already-named failure mode*
from earlier in this track — this isn't an arbitrary list, it's a checklist derived
directly from "what silently goes wrong" at each layer this track has covered.

### Correlating GPU-level and application-level metrics — the actual diagnostic skill

A dashboard showing DCGM metrics and a dashboard showing TTFT/TPOT, viewed separately,
answer different questions than the same two viewed *together*, on the same time axis.
This is the direct operational implementation of
[`12_llm_performance_engineering.md`'s decision tree](../phase5_llm_serving/12_llm_performance_engineering.md#the-performance-tuning-decision-tree):
a TPOT regression correlated in time with a drop in `DCGM_FI_PROF_DRAM_ACTIVE` (memory
bandwidth utilization actually falling, not the workload needing more of it) points
toward an infrastructure-layer cause (a degraded link, a thermal throttle) rather than a
workload-layer cause (more concurrent traffic, longer contexts) — the correlation itself
is the diagnostic signal, not either metric read in isolation.

### Tracing, not just metrics — where OpenTelemetry fits

Metrics (the catalog above) answer "what is the current state of this GPU/node." They
don't answer "which specific request, moving through which specific hops, took how long
at each step" — for a multi-node serving request (per
[`13_large_model_multi_gpu_inference/`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/README.md)'s
architecture), that requires **distributed tracing** — OpenTelemetry (OTel) spans
following one request through the load balancer, into the serving engine, across the
tensor-parallel group, and back. This is the tool that answers "why was THIS specific
request slow" when the aggregate metrics look fine on average — the individual-request
counterpart to the fleet-wide metric catalog above, and the concrete meaning behind
"OTel" in [`00_mental_model_and_roadmap.md`](../00_mental_model_and_roadmap.md)'s
original domain list, which named it without elaborating on the distinction from metrics.

## Deep-Dive: designing a dashboard around the diagnostic decision tree, not a metric dump

A common, avoidable mistake: building a dashboard that's simply every available DCGM
metric laid out in a grid, with no organizing logic. A dashboard that actually serves
[`12_llm_performance_engineering.md`'s decision tree](../phase5_llm_serving/12_llm_performance_engineering.md#the-performance-tuning-decision-tree)
is organized by *diagnostic question*, not by metric source:

```
Panel 1: "Is this a TTFT or TPOT problem?"      → TTFT/TPOT time series, split
Panel 2: "Is decode actually memory-bound       → SM util vs. DRAM active,
          right now, or something else?"           side by side, same time axis
Panel 3: "Is the interconnect healthy?"         → NVLink/cross-node throughput
                                                     vs. expected baseline
Panel 4: "Is a hardware fault involved?"        → XID/ECC/row-remap events,
                                                     annotated on the same timeline
Panel 5: "Is this a capacity/queueing problem,  → Queue depth, KV cache
          not a per-request problem?"              occupancy
```

This ordering directly mirrors the diagnostic order established in
`12_llm_performance_engineering.md` and `08_nccl_testing.md` — the dashboard's structure
*is* the decision tree, made visible, rather than a separate document a responder has to
remember to consult during an incident.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Full DCGM metric catalog scraped and dashboarded | Comprehensive, catches every failure mode named across this track | More cardinality/storage cost in Prometheus at fleet scale; needs deliberate dashboard organization to stay usable |
| Coarse utilization-only monitoring | Simple, low overhead | Structurally cannot distinguish "busy and productive" from "busy and stalled" — misses this track's most repeated failure mode entirely |
| Metrics only, no distributed tracing | Lower operational complexity | Cannot answer "why was this one specific request slow" when aggregates look healthy — a real gap for a multi-hop serving architecture |

## Failure Modes to Raise Proactively

- **Building a GPU dashboard around utilization alone** — the single most repeated
  failure mode across this entire track, restated at the observability-design level: a
  dashboard that can't distinguish compute-bound from memory-bound busy time reproduces
  the exact diagnostic gap every earlier chapter has warned against.
- **Treating application metrics (TTFT/TPOT) and infrastructure metrics (DCGM) as
  separate dashboards owned by separate teams** — the correlation between them, on a
  shared time axis, is where the actual diagnostic value lives; separating them
  structurally prevents that correlation from ever being made.
- **Having comprehensive metrics but no tracing** — leaves "why was this one request
  slow" unanswerable even when fleet-wide metrics show no obvious problem.

## Make It Yours

- If a Grafana instance with GPU dashboards is available anywhere in this workspace's
  existing build-outs, check explicitly whether SM utilization and memory bandwidth
  utilization are shown on the same panel/time axis, or as separate, uncorrelated panels
  — the exact distinction this chapter argues matters.

## Practice Questions

1. Why is `DCGM_FI_PROF_DRAM_ACTIVE` a more diagnostically useful metric than
   `DCGM_FI_DEV_GPU_UTIL` alone for catching a memory-bound stall, and why does neither
   one alone tell the full story?
2. What does distributed tracing answer that a comprehensive DCGM metric dashboard
   structurally cannot, for a multi-node serving deployment specifically?
3. A dashboard shows a TPOT regression at the same time as a drop in NVLink throughput —
   what does that correlation suggest as the likely root cause, versus a TPOT regression
   with no corresponding infrastructure-metric change?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "GPU fleet observability needs a metric catalog organized
around the specific failure modes GPU infrastructure actually has — compute utilization
alone can't distinguish productive work from a memory-bound stall, so it has to be paired
with HBM bandwidth utilization; NVLink throughput catches topology degradation; ECC/row-
remap metrics catch hardware faults before they become outright failures. The design
principle is correlating GPU-level metrics with application-level ones like TTFT/TPOT on
the same time axis, and pairing metrics with distributed tracing for the individual-
request question metrics alone can't answer."

**The follow-up-proof version**: be ready to name a specific pair of metrics that need to
be read together (SM utilization + DRAM active) rather than any single metric in
isolation, and explain concretely what each half of that pair rules in or out.

**Vocabulary builder**: *cardinality* (the number of distinct metric label combinations —
a real cost consideration at fleet scale), *distributed tracing* (following one request's
path across multiple services/hops, distinct from aggregate metrics), *thermal throttling*
(a GPU automatically reducing clock speed under high temperature, a real, checkable cause
of unexplained throughput regressions).
