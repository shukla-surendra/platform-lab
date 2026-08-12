# GPU Architecture: SMs, Cores, HBM, and Why the Shape Matters

Part of [Phase 2 — GPU Fundamentals](../README.md#phase-2-gpu-fundamentals). Read
[`00_mental_model_and_roadmap.md`](../00_mental_model_and_roadmap.md) first if you
haven't — this chapter is the foundation everything in Phases 3-7 assumes.

## Clarify: what problem does this chapter actually solve

Every other chapter in this track — NCCL, NVLink, Kubernetes GPU scheduling,
quantization, KV-cache math — treats "a GPU" as a black box with a memory size and a
FLOPS number. That's enough to reason about *serving* an LLM
(as [`13_large_model_multi_gpu_inference/tutorial.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tutorial.md)
does), but it's not enough to reason about *why* a GPU behaves the way it does under
real workloads — why a kernel launch has overhead, why memory bandwidth is usually the
real bottleneck rather than raw compute, why tensor cores exist as separate hardware from
CUDA cores, or why an H100 and an A100 with similar core counts can differ by 3-6x on
transformer workloads specifically. This chapter opens that box.

**Why a CPU mental model actively misleads here**: a CPU core is built to run one
instruction stream fast, with branch prediction, out-of-order execution, and deep caches
hiding latency. A GPU throws almost all of that away and instead runs *thousands* of
identical instruction streams simultaneously, hiding latency by having so much work in
flight that some of it is always ready while other parts wait on memory. If you reason
about a GPU the way you'd reason about a CPU — "this core is busy, therefore work is
progressing efficiently" — you'll misdiagnose exactly the failure mode
[`aws-production-architecture.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#monitoring-the-metrics-that-actually-matter-here)
already named: a GPU can look 100% "busy" while doing almost no useful work, stalled
waiting on memory or on a cross-node NCCL transfer.

## Core Concepts

### The hierarchy: GPU → SM → warp → thread

```
GPU
 └── N Streaming Multiprocessors (SMs)     — e.g. 132 SMs on an H100
      └── each SM contains:
           ├── CUDA cores        (FP32/INT32 execution units)
           ├── Tensor cores      (matrix-multiply-accumulate units)
           ├── Register file     (per-thread private storage)
           ├── Shared memory / L1 cache  (fast, SM-local, programmer-managed)
           └── Warp schedulers   (issue instructions to warps)
                └── Warps        — groups of 32 threads, executed in lockstep
                     └── Threads — the individual unit of work
```

- **A thread** is the smallest unit of work — conceptually one lane of computation, e.g.
  one output element of a matrix multiply.
- **A warp** is 32 threads that execute the *same instruction* at the same time
  (SIMT — Single Instruction, Multiple Threads). This is the detail that explains a lot
  of GPU-specific behavior: if threads within a warp take different branches
  (`if`/`else`), the warp executes *both* paths serially, masking off the threads that
  don't apply — divergent branching inside a warp is a real performance cost, not free
  the way it is on a CPU core.
- **An SM (Streaming Multiprocessor)** is the actual processing unit — it holds multiple
  warp schedulers, so it runs many warps concurrently, swapping between them to hide
  memory latency (while one warp waits on a memory load, another warp that's ready gets
  issued instead — this is *why* GPUs need so much parallel work in flight to reach full
  utilization, and why a workload with too little parallelism underuses the hardware no
  matter how "GPU-friendly" the math looks on paper).
- **The GPU** is many SMs (132 on H100, 108 on A100) plus shared L2 cache and HBM memory,
  all wired together on-die.

### CUDA cores vs. Tensor cores — genuinely different hardware

This is the single most common point of confusion, and it matters directly for LLM
workloads:

- **CUDA cores** are general-purpose ALUs — one core does one scalar FP32 or INT32
  operation per cycle. This is the "traditional" GPU compute path: good for arbitrary
  parallel work, not specialized for any particular math shape.
- **Tensor cores** are separate, specialized hardware that perform an entire small
  matrix-multiply-accumulate (e.g. a 4×4×4 FP16 matrix multiply) in one operation,
  instead of the many scalar multiply-adds a CUDA core would need to do the equivalent
  work. Since a transformer's dominant cost is matrix multiplication (attention
  projections, the MLP block), tensor cores are what actually determines an LLM's
  training/inference throughput on a given GPU — not the CUDA core count.

**Why this matters for interview follow-ups**: "more CUDA cores" is not the same claim as
"faster at LLM workloads." An H100's generational leap over an A100 is driven far more by
4th-gen Tensor Core improvements (and native FP8 support) than by CUDA core count growth
— this is the hardware fact underneath
[`tools-and-frameworks.md`'s quantization section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tools-and-frameworks.md#quantization-tooling)
calling FP8 "natively accelerated in H100/H200 hardware, not a software emulation."

### HBM: why GPU memory bandwidth, not just capacity, is the real budget

GPUs use **HBM (High Bandwidth Memory)** — stacked memory dies connected via a very wide
bus, physically located next to the GPU die on the same package (as opposed to a CPU's
DIMMs, which sit on the motherboard, farther away, on a narrower bus). Two numbers matter,
and they're independent:

| | Capacity | Bandwidth |
|---|---|---|
| What it means | How much data fits | How fast data moves between HBM and the SMs |
| H100 80GB SXM | 80 GB | ~3.35 TB/s |
| A100 80GB SXM | 80 GB | ~2.0 TB/s |

Capacity is the number [`tutorial.md`'s memory math](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tutorial.md)
already uses (500B params × 2 bytes ÷ 80GB per GPU). **Bandwidth is the number that
explains why LLM inference is usually memory-bound, not compute-bound**: generating one
token requires reading the *entire* set of model weights (and KV cache) from HBM once per
forward pass, even though the actual arithmetic on that data is comparatively cheap. This
is why TPOT (time-per-output-token) scales more directly with HBM bandwidth than with raw
FLOPS, and why a quantized model (fewer bytes to move per token) speeds up decode even
when the GPU's compute headroom was never the constraint — the mechanism underneath
[`13_quantization.md`](../phase5_llm_serving/13_quantization.md)'s throughput claims.

### The current NVIDIA data-center lineup, and what actually changes generation to generation

| GPU | SMs | Tensor Core gen | HBM | HBM bandwidth | NVLink |
|---|---|---|---|---|---|
| A100 | 108 | 3rd gen | 40/80 GB HBM2e | ~2.0 TB/s | 3rd gen, 600 GB/s |
| H100 | 132 | 4th gen (+ FP8) | 80 GB HBM3 | ~3.35 TB/s | 4th gen, 900 GB/s |
| H200 | 132 | 4th gen (+ FP8) | 141 GB HBM3e | ~4.8 TB/s | 4th gen, 900 GB/s |
| B200 | more SMs, 2-die package | 5th gen (+ FP4/FP6) | 192 GB HBM3e | ~8 TB/s | 5th gen, 1.8 TB/s |

The pattern across generations: SM/core counts grow modestly, but **HBM bandwidth,
tensor-core precision support, and NVLink bandwidth grow much faster** — direct evidence
that NVIDIA is optimizing for exactly the memory-bound, communication-bound shape of
transformer workloads, not for raw scalar compute. H200 vs. H100 is the clearest example:
same SM count, same compute ceiling — the entire generational win is more HBM capacity
and bandwidth, because that's what was actually constraining real workloads.

### Reading `nvidia-smi` and `nvidia-smi topo -m` against this model

Two commands turn this from theory into something checkable on real hardware:

```bash
nvidia-smi
# Shows: GPU utilization %, memory used/total, power draw, temperature — per GPU.
# The trap: "GPU-Util 98%" does NOT mean "doing useful work efficiently" — it means
# the SMs were issued *some* instruction in most of the sampled cycles. A kernel that's
# memory-bound and stalling on HBM reads can still show high utilization.

nvidia-smi topo -m
# Shows the interconnect matrix between every GPU pair on the node: NVLink (fastest),
# PCIe (slower, shared with other devices), or NODE/SYS (crossing NUMA/socket boundaries
# — much slower). This is the direct, checkable evidence for the "bandwidth tier"
# vocabulary from the roadmap doc's Articulate It section — before trusting a claim about
# which GPUs are NVLink-connected on a given instance, this is the command that proves it.
```

## Deep-Dive: why tensor parallelism stays intra-node

This directly grounds a claim [`tutorial.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tutorial.md)
makes without deriving it from hardware:

1. Tensor parallelism splits a single matrix multiply across GPUs — every forward pass,
   partial results must be combined (an all-reduce) *before* the next layer can proceed.
   This happens once per layer, dozens of times per forward pass.
2. NVLink between GPUs on the same node: ~900 GB/s (H100). EFA between nodes: ~400 Gbps
   ≈ 50 GB/s. That's roughly an 18x bandwidth gap.
3. An all-reduce that happens dozens of times per forward pass, at that frequency, can
   only tolerate the fast link — running it over the ~18x-slower inter-node fabric would
   make network time dominate wall-clock time, defeating the purpose of adding GPUs at
   all.
4. Pipeline parallelism, by contrast, only passes activations *between* pipeline stages —
   far less frequently, and each transfer is a full activation tensor rather than a
   per-layer partial-sum reduction. That lower frequency is what makes it tolerable on
   the slower inter-node link.

This is the mechanism-level answer behind the interview-framing claim in the roadmap doc
— not just "TP is intra-node because that's the convention," but the actual bandwidth
math that makes any other placement measurably worse.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| More SMs (scale out within a die) | More parallel work in flight | Diminishing returns once memory bandwidth is the bottleneck, not SM count |
| More HBM bandwidth (H200 over H100) | Directly speeds up memory-bound decode (TPOT) | Doesn't help a compute-bound workload (large-batch prefill) as much |
| Lower precision (FP8/INT4 on Tensor Cores) | Less HBM traffic per token, higher effective throughput | Accuracy trade-off — the exact tension [`13_quantization.md`](../phase5_llm_serving/13_quantization.md) covers |

## Failure Modes to Raise Proactively

- **Trusting `nvidia-smi` utilization alone as a health signal** — as shown above, high
  utilization is compatible with a memory-bound stall; DCGM's more granular counters
  (SM occupancy, memory throughput, PCIe/NVLink throughput) are what actually
  distinguish "busy and productive" from "busy and stalled," and are the metric
  [`17_observability_for_gpu_fleets.md`](../phase6_production_operations/17_observability_for_gpu_fleets.md)
  builds on.
- **Assuming CUDA core count predicts LLM throughput** — as shown above, Tensor Core
  generation and precision support is the number that actually matters for transformer
  workloads specifically.
- **Deploying a tensor-parallel group across a non-NVLink boundary** (e.g. spanning two
  nodes, or even two GPUs on the same node that aren't directly NVLink-connected on a
  partial-mesh topology) — everything still runs, just far slower, in a way that looks
  like a software bug until `nvidia-smi topo -m` is checked. The same class of "silent,
  expensive mistake" as skipping cluster placement groups, named in
  [`aws-production-architecture.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#networking-efa-and-placement-groups).

## Make It Yours

- Run `nvidia-smi topo -m` on any GPU instance you have access to (a `p5` node, a cloud
  dev box, even a single-GPU instance for the syntax) and read the actual matrix — name
  which pairs are NVLink vs. PCIe vs. crossing a NUMA boundary.
- Next time a serving deployment's throughput looks worse than the FLOPS numbers would
  predict, check HBM bandwidth utilization (via DCGM, once
  [`17_observability_for_gpu_fleets.md`](../phase6_production_operations/17_observability_for_gpu_fleets.md)
  is built) before assuming it's a software/batching problem.

## Practice Questions

1. Why can two GPUs both show 95%+ `nvidia-smi` utilization while one is doing 3x the
   useful work of the other?
2. An H200 and H100 have the same SM count and the same Tensor Core generation — where
   does the H200's real-world LLM-serving advantage actually come from?
3. Why does tensor parallelism need to stay within an NVLink domain, in terms of
   frequency of communication, not just "because it's the convention"?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "A GPU isn't one big processor — it's ~130 smaller processors
(SMs), each running thousands of threads in lockstep groups of 32 (warps), hiding memory
latency by always having more warps ready than can run at once. For LLM workloads
specifically, the two numbers that matter most aren't core count — they're Tensor Core
generation, because that's the actual matrix-multiply hardware, and HBM bandwidth,
because decode is memory-bound: every token requires re-reading the model's weights."

**The follow-up-proof version**: be ready to explain *why* generating one token is
memory-bound — walk through "the forward pass reads every weight from HBM once, but does
comparatively little arithmetic per byte read, so the constraint is how fast bytes move
from HBM to the SMs, not how many FLOPS the SMs could theoretically do" — and connect it
directly to why quantization (fewer bytes per weight) speeds up decode even without
touching compute.

**Vocabulary builder**: *SIMT* (Single Instruction, Multiple Threads — the warp execution
model), *occupancy* (how much of an SM's parallel capacity is actually in use, distinct
from utilization %), *memory-bound vs. compute-bound* (which resource actually gates
throughput — the central diagnostic question for any GPU performance problem), *warp
divergence* (the cost of branching differently within a 32-thread warp).
