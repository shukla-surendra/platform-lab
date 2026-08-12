# LLM Performance Engineering: Diagnosing and Tuning TTFT/TPOT for Real

Part of [Phase 5 — LLM Serving & Inference](../README.md#phase-5-llm-serving-inference).
Builds on [`03_gpu_architecture.md`](../phase2_gpu_fundamentals/03_gpu_architecture.md)
(memory-bound vs. compute-bound), [`13_quantization.md`](13_quantization.md) (one lever),
and the TTFT/TPOT metrics already named without a tuning methodology in
[`aws-production-architecture.md`'s monitoring section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#monitoring-the-metrics-that-actually-matter-here).
This chapter is that methodology: given a bad TTFT or TPOT number, what do you actually
check, in what order, and why.

## Clarify

Every earlier chapter in this track has established individual facts — decode is
memory-bound, quantization moves fewer bytes, NCCL's algorithm choice affects cross-node
latency. This chapter is where those facts become a diagnostic *procedure*: a real
performance incident ("TPOT regressed 40% after last week's deploy," "TTFT is fine at low
load but spikes under traffic") requires knowing which of several possible causes to check
first, not re-deriving first principles from scratch under pressure.

## Core Concepts

### Prefill and decode are different compute shapes — this is the root of everything else

A transformer forward pass for serving splits into two phases with genuinely different
performance characteristics:

- **Prefill** — processing the entire input prompt at once, computing attention over all
  prompt tokens simultaneously. This is **compute-bound**: large matrix multiplications
  with high arithmetic intensity (a lot of FLOPS per byte moved from HBM), so it benefits
  from raw Tensor Core throughput and larger batch sizes. **TTFT is dominated by prefill**
  — the first token can't be produced until the whole prompt has been processed once.
- **Decode** — generating one token at a time, each step re-reading the full model weights
  (and growing KV cache) from HBM for comparatively little new arithmetic. This is
  **memory-bandwidth-bound**, the mechanism already established in
  [`03_gpu_architecture.md`'s HBM section](../phase2_gpu_fundamentals/03_gpu_architecture.md#hbm-why-gpu-memory-bandwidth-not-just-capacity-is-the-real-budget).
  **TPOT is dominated by decode.**

This split is *why* TTFT and TPOT need separate monitoring
(`aws-production-architecture.md` already asserts this) — they're not two views of one
underlying bottleneck, they're two different bottlenecks entirely, and a fix for one can
leave the other untouched or even make it worse.

### The performance-tuning decision tree

```
Symptom: TTFT is bad
  → Prefill is compute-bound → check:
      - Batch size / concurrent prefill load (more concurrent prompts
        competing for the same compute)
      - Prompt length (quadratic-ish attention cost growth with context)
      - Raw Tensor Core throughput available (is a lower-tier GPU or a
        MIG-sliced partial GPU actually handling this, per
        10_gpu_scheduling_mig_sharing.md?)
      - Chunked prefill / prefill-decode overlap settings (see below)

Symptom: TPOT is bad
  → Decode is memory-bandwidth-bound → check:
      - HBM bandwidth utilization via DCGM (03_gpu_architecture.md,
        04_cuda_ecosystem.md) — is the GPU actually saturating its
        available bandwidth, or stalling on something else (cross-node
        NCCL wait, per 06_nccl_and_collective_communication.md)?
      - KV cache size relative to available HBM (growing context window
        directly grows per-step HBM traffic — see 14_model_memory_estimation.md)
      - Precision (is this workload still at FP16 when FP8/INT4 per
        13_quantization.md would reduce bytes moved per step?)
      - Batch size (counterintuitively, larger batches can IMPROVE
        decode throughput per-request by amortizing weight reads across
        more concurrent sequences — see batching below)

Symptom: Both are bad, together, only under concurrent load
  → Likely a batching/scheduling problem, not a per-request compute
    problem — check the serving engine's batching strategy first
```

**Why this tree matters as the actual skill being tested**: naming "TTFT" and "TPOT" is
table stakes; routing a specific bad number to the correct half of this tree, and then to
the correct specific check within that half, is what separates a real diagnostic answer
from a vocabulary list.

### Batching strategies — the lever that touches both metrics at once

- **Static batching** — wait for a fixed batch size to fill, run it together, return all
  results together. Simple, but every request in the batch waits for the *slowest*
  request to finish — a short request stuck behind a long one pays unnecessary latency.
- **Dynamic batching** — batches form as requests arrive within a time window, but the
  batch still runs as one fixed unit start-to-finish, same tail-latency problem as static
  batching, just with better throughput on average.
- **Continuous (in-flight) batching** — the technique vLLM and modern serving engines
  actually use: as soon as any sequence in the current batch finishes generating, a new
  request can be inserted into the batch *immediately*, without waiting for every other
  sequence to finish. This is what makes a serving engine's throughput scale well under
  real, bursty traffic instead of the batch always being gated by its slowest member.

**The direct connection to decode's memory-bound nature**: continuous batching's
throughput win isn't accidental — because decode is memory-bandwidth-bound (weights get
read from HBM regardless of batch size), processing more sequences *in the same decode
step* amortizes that HBM read across more useful work, directly increasing tokens/sec
without a proportional increase in HBM traffic. This is the mechanism-level reason
"increase batch size" is a real decode-throughput lever, not just a rule of thumb.

### Chunked prefill — trading a small TTFT cost for a large TPOT stability win

A long prompt's prefill can itself block decode steps for *other* concurrent requests
sharing the same GPU (prefill is compute-bound and can monopolize the SMs for its
duration). **Chunked prefill** splits a long prompt's prefill into smaller pieces,
interleaved with other requests' decode steps, so one long prompt doesn't cause a
latency spike in every other concurrent request's TPOT. This is a direct, practical
answer to a real production symptom: "TPOT is fine on average but spikes intermittently"
often traces to exactly this — one large concurrent prefill starving decode steps for
everyone else, fixable by chunked prefill rather than by any of the per-request tuning
above.

## Deep-Dive: profiling the actual bottleneck instead of guessing

The decision tree above tells you *what class* of problem to suspect; profiling tools
confirm it directly rather than trusting inference from symptoms alone:

- **`nvidia-smi` / DCGM, at the coarse level** (from
  [`03_gpu_architecture.md`](../phase2_gpu_fundamentals/03_gpu_architecture.md#reading-nvidia-smi-and-nvidia-smi-topo-m-against-this-model)
  and [`04_cuda_ecosystem.md`](../phase2_gpu_fundamentals/04_cuda_ecosystem.md)) — check
  SM occupancy vs. memory bandwidth utilization together; a decode-bound step should show
  high HBM bandwidth utilization with comparatively lower SM compute utilization — if SM
  utilization is *also* high during decode, something unexpected is consuming compute
  that shouldn't be there for a memory-bound phase.
- **NVIDIA Nsight Systems** — a timeline-level profiler that shows exactly which CUDA
  kernels ran, for how long, and whether GPU time is being lost to gaps (the GPU idle,
  waiting on something — a NCCL collective, a Python-side scheduling delay, a CPU-side
  bottleneck feeding work to the GPU too slowly). This is the tool that answers "is the
  GPU actually the bottleneck at all, or is it starved by something upstream" — a real,
  common confusion this chapter's decision tree assumes has already been ruled out.
- **PyTorch Profiler** — framework-level, shows time spent per operator (which specific
  cuBLAS/cuDNN calls, per
  [`04_cuda_ecosystem.md`](../phase2_gpu_fundamentals/04_cuda_ecosystem.md#cublas-and-cudnn-the-two-libraries-that-do-almost-all-the-real-work),
  are actually consuming the most time) — the right tool once Nsight Systems has already
  confirmed the GPU itself is the bottleneck, not something upstream of it.

**The diagnostic order that avoids wasted effort**: DCGM/`nvidia-smi` first (cheap, always
running, answers "compute-bound or memory-bound") → Nsight Systems next (confirms the GPU
isn't idle/starved) → PyTorch Profiler last (only once the first two have narrowed the
problem to "which specific operation on the GPU itself").

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Larger batch size | Better decode throughput (HBM read amortized over more sequences) | Higher per-request latency variance; more KV cache memory consumed simultaneously |
| Chunked prefill | Smoother TPOT for concurrent requests during long prompts | Slightly higher TTFT for the long prompt itself (its prefill is spread out, not run as one fast burst) |
| Continuous batching over static/dynamic | Much better tail latency and throughput under real bursty traffic | More complex scheduler implementation inside the serving engine — a reason to prefer an engine that already does this well (vLLM, per `tools-and-frameworks.md`) over a custom implementation |

## Failure Modes to Raise Proactively

- **Applying a decode-side fix (quantization, batch size) to a TTFT problem, or vice
  versa** — since the two are dominated by different compute shapes, a fix aimed at the
  wrong half of the pipeline can leave the actual regression untouched while looking like
  "we tried something."
- **Trusting `nvidia-smi` utilization alone to diagnose a bottleneck** — the exact failure
  mode from `03_gpu_architecture.md`, restated here in its performance-engineering
  context: high utilization during a memory-bound decode step doesn't rule out the GPU
  being starved by something upstream; Nsight Systems is the tool that actually confirms
  this, not inference from one utilization number.
- **Increasing batch size to fix TPOT without checking KV cache headroom first** — larger
  batches consume more KV cache memory simultaneously; pushing batch size up without
  checking the memory budget from
  [`14_model_memory_estimation.md`](14_model_memory_estimation.md) risks trading a
  latency problem for an OOM incident.

## Make It Yours

- Next time a serving deployment's latency is reviewed, explicitly separate the
  conversation into TTFT and TPOT before proposing any fix — naming which one is actually
  regressed is the first, non-optional step in this chapter's decision tree.
- If Nsight Systems or the PyTorch Profiler is available in a project you're working on,
  run it once on a real serving workload and identify a genuine gap (GPU idle time) if one
  exists — turns "the GPU might be starved" from a hypothesis into something directly
  observed.

## Practice Questions

1. A team increases batch size to fix a TPOT regression and it works — explain the
   mechanism, in terms of HBM bandwidth, for why a memory-bound operation gets faster
   per-request as batch size grows (up to a point).
2. TTFT is fine under light load but spikes under concurrent traffic, while TPOT stays
   roughly stable — what's the most likely cause, and what serving-engine feature
   addresses it directly?
3. Why is checking `nvidia-smi`/DCGM before reaching for Nsight Systems the right
   diagnostic order, rather than starting with a detailed kernel-level profiler?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "TTFT and TPOT are dominated by different phases with
different bottlenecks — prefill is compute-bound and drives TTFT, decode is
memory-bandwidth-bound and drives TPOT — so tuning them requires different levers:
prefill benefits from raw compute and chunking to avoid starving concurrent decode steps,
decode benefits from continuous batching (which amortizes HBM reads across more
sequences) and quantization (which reduces bytes moved per step). Diagnosing a real
regression means routing the symptom to the right half of that split before reaching for
a fix, then confirming with DCGM and Nsight Systems rather than guessing."

**The follow-up-proof version**: be ready to explain *why* continuous batching improves
decode throughput specifically in terms of the HBM-bandwidth mechanism from
`03_gpu_architecture.md`, not just "it batches more efficiently" — the interviewer's
follow-up is almost always "why does that help," and the memory-bound mechanism is the
actual answer.

**Vocabulary builder**: *arithmetic intensity* (FLOPS performed per byte moved from
memory — the number that determines whether an operation is compute-bound or
memory-bound), *chunked prefill* (splitting a long prompt's prefill to avoid starving
concurrent decode steps), *tail latency* (the worst-case, not average, latency — what
batching-strategy choice most directly affects).
