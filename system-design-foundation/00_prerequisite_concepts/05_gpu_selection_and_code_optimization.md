# Prerequisite Concepts, Part 5: Choosing a GPU, and Making Your Code Actually Use It

[Part 4](04_cpu_vs_gpu.md) covered *why* GPUs are built the way they are. This part is
the practical follow-on: which specific GPU fits which job, and — the part that matters
more than the hardware choice most of the time — how to write and configure code so it
actually exercises the hardware you're paying for, instead of leaving it idle the way
[tricky scenario 14](../ml_system_design/12_tricky_scenarios_14_gpu_underutilized_sequential_pipeline.md)
did.

## A Practical Catalog: Which GPU for Which Job

This extends the [training-class vs. inference-class distinction from Part
4](04_cpu_vs_gpu.md#not-all-gpu-memory-is-the-same-gddr6-vs-hbm) into an actual shopping
list. Figures below are illustrative and approximate — generations and pricing move
quickly; the *tier each GPU sits in*, and *why*, is the durable part.

| Tier | Example GPUs | Memory type | Typical VRAM | Common cloud instance | Best for |
|---|---|---|---|---|---|
| **Consumer / prototyping** | RTX 4090, RTX 3090 | GDDR6/6X | 24 GB | (local workstation, not typically cloud-rented) | Local experimentation, small-model fine-tuning, learning — no ECC memory or NVLink, not built for 24/7 datacenter reliability |
| **Inference-class (cloud)** | T4, A10/A10G, **L4** | GDDR6 | 16-24 GB | AWS `g4dn`, `g5`, `g6` | Steady-state, cost-efficient serving of a model that's already trained — the [`g6.2xlarge` example from Part 4](04_cpu_vs_gpu.md#worked-example-is-an-nvidia-l4-g62xlarge-a-good-fit-for-a-receipt-fraud-classifier) is this tier |
| **Training-class (cloud, previous-gen)** | V100, A100 | HBM2/HBM2e | 16-80 GB | AWS `p3`, `p4d` | Large-batch training, fine-tuning bigger models, still widely deployed and meaningfully cheaper than the current flagship |
| **Training-class (cloud, current-gen)** | H100, H200 | HBM3/HBM3e | 80-141 GB | AWS `p5`, `p5e` | Large-scale pretraining, the biggest fine-tuning jobs, LLM serving at the highest throughput tier — includes a "Transformer Engine" specifically accelerating the attention/matmul patterns LLMs use heavily |
| **Non-NVIDIA alternative** | AMD MI300X | HBM3 | ~192 GB | (available on some clouds, smaller ecosystem) | Workloads where raw memory capacity matters more than CUDA-ecosystem tooling maturity — worth knowing exists, not the default choice for most teams today |
| **Not a GPU at all** | Google TPU | HBM | Varies by generation | GCP only | An ASIC (purpose-built chip, not a general GPU) designed specifically for the matrix-multiply-heavy pattern of neural nets — mentioned here so you know NVIDIA isn't the only option, not because most teams should reach for it by default |

**The one-question shortcut that maps to most of this table**: *is this workload training
a model, or serving an already-trained one?* Training wants HBM's bandwidth and the
biggest VRAM you can afford, because you're moving huge batches continuously. Inference
usually doesn't need that bandwidth — a GDDR6-based inference GPU is often both cheaper
*and* the architecturally correct choice, not a compromise (exactly the reasoning worked
through in Part 4's L4 example).

## Profile Before You Optimize

Before touching any technique below: **measure what's actually the bottleneck first.** A
GPU workload is bottlenecked by exactly one of three things at a time — compute (the
cores are busy, doing real work, and that's the ceiling), memory bandwidth (the cores are
waiting on data moving in/out of VRAM), or data loading (the GPU is waiting on the CPU
side to hand it the next batch, per [tricky scenario
14](../ml_system_design/12_tricky_scenarios_14_gpu_underutilized_sequential_pipeline.md)). Tools like
`nvidia-smi` (quick utilization check), NVIDIA Nsight Systems, or a framework's built-in
profiler (`torch.profiler`) tell you which one you're actually facing. **Applying a
compute optimization (like mixed precision) to a data-loading-bound pipeline does
nothing** — this is the same diagnostic discipline as the [scaling-efficiency deep-dive
in the distributed training
tutorial](../ml_system_design/07_distributed_training_serving.md#deep-dive-diagnosing-poor-scaling-efficiency),
applied to a single GPU instead of a whole cluster.

## Precision: Why FP16/BF16/INT8 Matter, From First Principles

Every number a model computes with is stored in some number of bits — and that choice
cascades into memory, bandwidth, and speed all at once.

- **FP32 (32-bit float)**: the traditional default, high precision, but every number costs
  4 bytes — the most memory, the most bandwidth to move, and the slowest to compute on
  much of modern GPU hardware.
- **FP16 / BF16 (16-bit float)**: half the bytes per number — automatically halves memory
  footprint and the bandwidth cost of moving data, *and* modern GPUs have dedicated
  **Tensor Cores** that compute matrix multiplication in these lower precisions
  dramatically faster than FP32, as a genuine hardware feature, not just a memory trick.
  BF16 keeps FP32's exponent range (fewer precision-loss surprises during training) at
  FP16's size, which is why it's become the common default for training; FP16 remains
  common for inference.
- **INT8 / INT4 (quantization)**: represent weights as 8-bit or 4-bit integers instead of
  floats at all — a further step down in memory and bandwidth, at a real (but often
  acceptable, especially for inference) accuracy cost. This is the same **quantization**
  concept already named in [Part 4's memory
  section](04_cpu_vs_gpu.md#memory-why-a-gpu-needs-its-own-physically-separate-memory) —
  worth connecting explicitly: quantization is a precision choice, not a separate magic
  trick.

**Why this is usually the single highest-leverage code change available**: switching a
training or inference job to mixed precision (BF16/FP16 instead of FP32) often yields a
large, close-to-free speedup — it directly relieves whichever of the two real bottlenecks
(memory bandwidth or Tensor Core throughput) you were hitting, for a few lines of
framework configuration (e.g. PyTorch's `torch.cuda.amp.autocast` / `bfloat16` dtype),
with limited downside for most workloads. It's usually worth trying before any of the
more invasive techniques below.

## Kernel Launch Overhead and Fusion

**The problem**: every discrete GPU operation (a "kernel" — one matrix multiply, one
activation function, one elementwise add) has a small, fixed launch overhead, and
naively-written model code often issues many small, separate kernel calls in sequence —
each one also round-tripping its result back out to VRAM before the next kernel reads it
back in. At small operation sizes, that overhead and unnecessary memory traffic can
dominate the actual useful compute time.

**Kernel fusion** combines multiple sequential operations into a single kernel — paying
the launch overhead once instead of N times, and keeping intermediate results in fast
on-chip memory (registers/shared memory, several tiers faster than VRAM, the same
locality principle as [caching from
Fundamentals](../ml_system_design/00_interview_framework_fundamentals.md#caching)) instead of writing them out to
VRAM and reading them back for the next op.

**You rarely hand-write fused kernels yourself** — the practical version of this is
letting a compiler do it: `torch.compile` (PyTorch), XLA (JAX/TensorFlow), or TensorRT
(NVIDIA's inference-specific compiler) analyze your model's computation graph and
automatically fuse operations, select optimal kernel implementations, and sometimes apply
precision casting for you. Knowing *why* these tools produce a speedup (fewer kernel
launches, less VRAM round-tripping) is what separates "I ran `torch.compile()`" from
understanding what actually happened.

## Keeping the GPU Fed: Data Transfer and Batching

- **Minimize host-device transfers.** Every `.cpu()`, `.numpy()`, or `.to("cuda")` call
  crosses the slowest link in [Part 4's three-tier memory
  hierarchy](04_cpu_vs_gpu.md#memory-why-a-gpu-needs-its-own-physically-separate-memory) —
  a stray transfer inside a hot loop (common when debugging with a `print()` that forces a
  sync, or logging a metric every step) can silently dominate runtime.
- **Pinned (page-locked) memory + asynchronous transfer.** Normal ("pageable") host memory
  requires an extra copy step before the GPU can DMA-transfer it; pinned memory allows a
  direct transfer, and combined with CUDA streams, lets the *next* batch's data transfer
  overlap with the *current* batch's compute instead of happening strictly before it
  (PyTorch: `DataLoader(..., pin_memory=True)` plus `.to(device, non_blocking=True)`).
  This is the single-GPU version of the same idea as overlapping CPU and GPU stages in
  [tricky scenario 14's fix](../ml_system_design/12_tricky_scenarios_14_gpu_underutilized_sequential_pipeline.md#the-fix).
- **Batch size is a real latency-vs-throughput dial, not a free knob.** Bigger batches
  give the GPU more parallel work per kernel launch (higher throughput, better
  utilization) but increase the latency any single item in that batch waits to be
  returned, and risk hitting VRAM limits. This is the [latency-vs-throughput axis from
  Part 1](01_performance_and_scale.md#latency-vs-throughput) again — tune batch size
  against whichever side of that trade-off your actual requirement cares about more, the
  same way [continuous batching in the vLLM
  deep-dive](../ml_system_design/06_rag_llm_serving_at_scale.md#deep-dive-llm-serving-internals-vllm-on-triton)
  does it dynamically rather than picking one fixed size forever.

## The Rest of the Toolkit, By Pointer

Two categories of GPU optimization are already covered elsewhere in this repo in enough
depth that they're not repeated here — flagged so this doc's coverage feels complete, not
incomplete:

- **Memory-scarcity techniques** (when VRAM capacity, not speed, is the constraint):
  quantization, gradient checkpointing, and PagedAttention — see [Part 4's memory
  section](04_cpu_vs_gpu.md#memory-why-a-gpu-needs-its-own-physically-separate-memory).
- **Multi-GPU parallelism** (when one GPU's capacity is the constraint, not just its
  utilization): data/model/pipeline parallelism, gradient synchronization strategies,
  diagnosing poor multi-GPU scaling efficiency — see the [distributed training
  tutorial](../ml_system_design/07_distributed_training_serving.md) in full.

## Quick Self-Check

- Given a workload description, could you place it in the right row of the GPU catalog
  table and justify *why*, not just name a GPU model from memory?
- Why is profiling before optimizing not just good practice but a genuine prerequisite —
  what happens if you apply a compute-side fix to a data-loading-bound pipeline?
- Why does switching to BF16/FP16 usually help both memory *and* speed simultaneously,
  rather than trading one for the other?
- Why does kernel fusion reduce VRAM traffic, not just reduce launch-overhead count?
- Why is "increase the batch size" not a strictly-better lever — what does it cost you?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **One-question-shortcut framing (the default for 'which GPU should I use'):** "I'd
  collapse the whole GPU catalog to one question first — is this training or serving an
  already-trained model? Training wants HBM bandwidth and the biggest VRAM affordable;
  serving usually doesn't need that bandwidth, so a GDDR6-based inference GPU is often the
  architecturally correct choice, not a compromise."
- **Diagnose-before-optimize framing (the default for any 'how do I speed this up'
  question):** "I wouldn't reach for mixed precision or kernel fusion first — I'd profile
  to find out whether this is compute-bound, memory-bandwidth-bound, or data-loading-bound,
  because applying a compute fix to a data-loading bottleneck does nothing measurable."
- **Free-lunch framing (good for explaining why precision is usually the first lever to
  pull):** "Mixed precision is close to a free win — it relieves memory bandwidth and
  unlocks dedicated Tensor Core throughput simultaneously, for a couple of lines of
  framework config, before I'd reach for anything more invasive like custom kernel work."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **Tensor Core** (n. phrase) — dedicated GPU hardware that computes matrix multiplication
  in lower precision (FP16/BF16/INT8) dramatically faster than general-purpose cores.
- **kernel launch overhead** (n. phrase) — the small, fixed cost of issuing each discrete
  GPU operation; the reason many small unfused operations can underperform one fused one.
- **pinned memory** (n. phrase) — page-locked host memory that allows a direct DMA
  transfer to the GPU, enabling overlap between data transfer and compute.
- **mixed precision** (n. phrase) — computing with a lower-precision format (BF16/FP16)
  instead of FP32 for most of a model's operations, trading some numerical precision for
  speed and memory.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…is a real dial, not a free knob"** — a fluent way to argue a parameter (batch size)
  has a genuine cost on the other side, not just an upside.
- **"…is the durable part, not the specific numbers"** — useful when quoting hardware
  specs that will age, to signal you understand the relationship survives even as the
  numbers shift.
- **amortize** (v.) — to spread a fixed cost across more units so its per-unit impact
  shrinks. *"Kernel fusion amortizes launch overhead across what used to be several
  separate calls."*
- **"…does nothing measurable"** — a sharp, quotable way to argue a mismatched
  optimization (applying a compute fix to an I/O-bound problem) isn't just suboptimal,
  it's wasted effort entirely.

---

**Previous:** [Part 4: CPU vs. GPU](04_cpu_vs_gpu.md)  |  **Next:** [Part 6: Mechanical Sympathy & the Physics of Latency](06_mechanical_sympathy_and_physics_of_latency.md)
