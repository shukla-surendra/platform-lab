# Prerequisite Concepts, Part 4: CPU vs. GPU, From First Principles

[Parts 1-3](01_performance_and_scale.md) covered general distributed-systems vocabulary.
This part is specific to the ML-heavy tutorials in this repo ([distributed
training](../ml_system_design/07_distributed_training_serving.md), [LLM
serving](../ml_system_design/06_rag_llm_serving_at_scale.md), the [GPU cost
scenarios](../ml_system_design/12_tricky_scenarios_04_gpu_cost_spike.md)) — all of which assume you already
understand *why* GPUs work the way they do, not just that "GPUs are for AI." If you have
solid CPU intuition but have never had GPU architecture explained from scratch, start here.

## The Core Design Question: Optimize for Latency, or Optimize for Throughput?

This is the [latency-vs-throughput distinction from Part
1](01_performance_and_scale.md#latency-vs-throughput), expressed in silicon rather than
software:

- **CPU: latency-optimized.** A few complex cores, each built to finish *one* instruction
  stream as fast as possible — deep pipelines, branch prediction, out-of-order execution,
  large private caches. Think a handful of expert generalists, each capable of complex,
  varied reasoning, working on different problems independently.
- **GPU: throughput-optimized.** Thousands of simple cores, each individually much weaker,
  built to do the *same* operation across massive amounts of data simultaneously. Think an
  army of line cooks who can each only do one simple repetitive task — but there are
  thousands of them, so the aggregate output dwarfs a handful of generalists on any task
  that's actually parallelizable.

Neither is "better" — they're optimized for opposite ends of the same axis. A CPU core
also typically runs at a higher clock speed than a single GPU core, for the same reason:
it's doing one thing at a time and wants that one thing done fast, while a GPU core is
betting on parallel volume over per-operation speed.

## Cores: How Many, and What Kind

| | CPU | GPU |
|---|---|---|
| Core count | Single digits to a few dozen | Thousands (high-end GPUs: 10,000+) |
| Core complexity | High — out-of-order execution, branch prediction, deep pipeline | Low — a simple arithmetic unit (ALU), no fancy scheduling logic |
| Execution model | Each core runs an independent instruction stream (MIMD) | Cores execute in lockstep groups (SIMT) |
| Good at | Branchy, sequential, varied logic — an OS scheduler, a web server handling diverse requests | Uniform, repetitive, massively parallel math — the same operation applied to millions of independent data points |

**The mechanism that makes GPU cores different from "many small CPU cores"**: GPU cores
are grouped into clusters called **Streaming Multiprocessors (SMs)**, and within an SM,
cores execute in groups of 32 called a **warp** — every core in a warp executes the *same
instruction*, on the *same clock cycle*, on different data (this is **SIMT**: Single
Instruction, Multiple Threads, a variant of the classic SIMD idea). It's not 10,000
independent little CPUs; it's a much smaller number of instruction *streams*, each fanned
out across a warp of cores executing that one stream's instructions in lockstep.

**The failure mode this creates — warp divergence**: if code inside a warp hits a branch
(`if/else`) and different threads in that warp need different paths, the hardware can't
actually run both paths simultaneously — it executes one path with the divergent threads
masked off (idle), then the other path, serially. A warp full of branchy, data-dependent
control flow gets none of the parallelism benefit and just runs slower than the same code
would on a CPU. This is the direct, mechanical reason GPUs are excellent at dense linear
algebra and poor at branch-heavy general-purpose code — it's not a software limitation,
it's the hardware's execution model.

## Why This Shape Happens to Match Neural Networks

GPUs weren't designed for AI — they were built for rendering graphics, where the same
operation (shade this pixel, transform this vertex) applies independently to millions of
data points every frame: an "embarrassingly parallel" workload in the same sense the
[ingestion pipeline
tutorial](../ml_system_design/02_ingestion_pipeline.md#reference-architecture) uses that term for
parallel transcoding. **Matrix multiplication — the core operation inside every neural
network layer — has that exact same shape**: apply the same multiply-accumulate operation
across a huge grid of numbers, independently, over and over. Deep learning didn't design
GPUs for itself; it discovered hardware that already happened to fit the shape of its
workload, which is why the entire modern AI industry runs on chips originally built to
render video games.

## Memory: Why a GPU Needs Its Own, Physically Separate Memory

**The bottleneck this solves**: if a GPU's thousands of cores had to fetch every piece of
data from the CPU's system RAM over the connecting bus (PCIe), they'd spend most of their
time idle, waiting on data — a GPU computing at massive parallel throughput needs data
delivered at a matching rate, and a general-purpose link designed to connect arbitrary
peripherals to a CPU isn't built for that. This is the exact same first-principles idea as
[caching from Fundamentals](../ml_system_design/00_interview_framework_fundamentals.md#caching) — data physically close
to where it's consumed is fast, data far away is slow — just realized in hardware instead
of software.

The result: a GPU carries its own on-board memory, generically called **VRAM** — some
form of dedicated, physically-close memory, connected by a much wider bus than a
general-purpose system has any reason to build. There are three distinct speed tiers worth
knowing by name, illustrative and approximate (exact figures shift by generation — the
*relationship*, not the specific numbers, is the point):

| Link | Rough relative speed | What lives here |
|---|---|---|
| GPU's own VRAM (device memory) | Fastest — the whole reason it exists | Model weights and activations actually being computed on right now |
| CPU system RAM (host memory) | Meaningfully slower than VRAM | Everything not currently on the GPU |
| PCIe link between CPU and GPU | Slowest of the three, by a wide margin | The path data crosses to move between the two |

**Why this matters practically, not just architecturally:**

- **GPU memory is small and expensive; system RAM is large and cheap.** A GPU might carry
  tens of gigabytes of HBM; a server's system RAM can easily be a terabyte or more. GPU
  memory is the scarce resource in almost every ML infrastructure decision.
- **Moving data between the two is an explicit, sometimes costly step** — `.to("cuda")` in
  PyTorch isn't a formality, it's a real transfer across the slowest link in the chain, and
  doing it unnecessarily (e.g., in a hot loop) is a common, avoidable performance bug.
- **Running out of GPU memory is a distinctly different failure from running out of RAM**
  — a "CUDA out of memory" error is its own category of production incident, and it's the
  direct motivation behind essentially every GPU-memory-efficiency technique already
  covered elsewhere in this repo: **quantization** (represent numbers with fewer bits so
  the same model fits in less memory), **gradient checkpointing** (recompute intermediate
  values during backpropagation instead of storing all of them, trading compute for
  memory), and **PagedAttention** (the [vLLM serving
  deep-dive](../ml_system_design/06_rag_llm_serving_at_scale.md#deep-dive-llm-serving-internals-vllm-on-triton)
  — non-contiguous, on-demand memory allocation for the KV cache, borrowed directly from
  how operating systems page virtual memory). None of these are arbitrary clever tricks —
  they're all the same underlying constraint (HBM is small and precious) solved from
  different angles.

## Not All GPU Memory Is the Same: GDDR6 vs. HBM

It's tempting to treat "VRAM" as one thing, but the memory *technology* underneath it
splits GPUs into two genuinely different product categories — and which one a specific
GPU uses tells you what it was actually built for.

- **HBM (High Bandwidth Memory)**: memory dies physically stacked directly on top of the
  GPU package, connected by an extremely wide bus. Very high bandwidth (order-of-magnitude
  ~3 TB/s on a flagship training GPU), but expensive to manufacture and power-hungry
  (a training-class GPU can draw ~700W). Found on **training-class GPUs** — NVIDIA's
  A100/H100 class — built for the sustained, massive data movement large-batch training
  demands.
- **GDDR6**: a cheaper, more power-efficient memory technology descended from consumer
  graphics cards — meaningfully lower bandwidth than HBM (order-of-magnitude ~300 GB/s, a
  full order of magnitude less), but dramatically cheaper and cooler-running (as low as
  ~70W). Found on **inference-class GPUs** — NVIDIA's T4, A10, and **L4** — built for
  steady-state, cost-efficient serving rather than training throughput.

**Why this is the same latency-vs-throughput/cost trade-off again, one layer down**:
training genuinely needs to move enormous batches through memory as fast as possible —
bandwidth is the bottleneck, so HBM's cost and power draw are worth paying. Inference,
by contrast, is typically one (or a handful of) request at a time — the model's weights
sit in memory and get reused repeatedly, without needing anywhere near HBM's bandwidth to
stay fed. **Paying for HBM on an inference workload is paying for a bottleneck-relief you
don't have** — which is exactly why a purpose-built inference GPU trades that unnecessary
bandwidth for a fraction of the cost and power draw instead.

### Worked Example: Is an NVIDIA L4 (g6.2xlarge) a Good Fit for a Receipt-Fraud Classifier?

A concrete instance-selection decision, worked the way you'd want to justify it in an
interview — with numbers, not vibes, the same discipline as the
[serverless-vs-EKS receipt-processing
deep-dive](../ml_system_design/02_ingestion_pipeline_serverless_vs_eks_receipt_processing.md#cost-model-the-actual-numbers).

**The workload**: score a submitted receipt image as genuine or fake — a single-image (or
small-batch) inference call, not training, and not a workload that needs to move gigabytes
per request.

**The instance** (AWS `g6.2xlarge`, illustrative specs — check current AWS documentation
for exact figures): 8 vCPUs, 32 GiB system RAM, 1x NVIDIA L4 GPU (~7,424 CUDA cores, 24 GB
**GDDR6**, ~300 GB/s memory bandwidth, 72W), ~$0.98/hr on-demand.

**Why L4 specifically fits, reasoned from first principles, not just "AWS suggested it":**

1. **This is an inference workload, so HBM's bandwidth advantage is mostly wasted here.**
   The workload characteristic (one image at a time, not massive training batches) matches
   exactly the profile GDDR6-based inference GPUs are built for — you'd be paying a
   training-class GPU's cost and power premium for bandwidth this workload structurally
   can't use.
2. **24 GB of VRAM is generous headroom, not a tight fit.** A receipt-classification model
   (a CNN or a lightweight vision transformer, likely with an OCR-adjacent feature
   extraction step upstream) almost certainly needs a small fraction of that — leaving
   room for meaningful batch sizes under peak load without risking the "CUDA out of
   memory" failure mode, and room to grow the model later without re-architecting the
   serving tier.
3. **8 vCPU / 32 GiB system RAM is sized to feed the GPU, not to be the bottleneck.**
   Image decode and any preprocessing before the model call happen on CPU; this is enough
   headroom that the GPU — the expensive, purpose-built part — stays the thing doing the
   actual work, not waiting on CPU-side preprocessing.
4. **$0.98/hr is meaningfully cheaper than a training-class instance would cost for the
   same job** — an A10G- or A100-class instance would cost multiples of this per hour,
   for bandwidth and power capacity this specific workload has no use for.

**The one thing worth checking, not assuming — traffic shape.** A single warm
`g6.2xlarge` is a clean fit if receipt submissions arrive at a roughly steady rate. If
traffic is genuinely bursty (a spike after a batch upload job, say), this instance size
should be the *baseline* tier with autoscaling layered on top, not the only tier — exactly
the [scale-to-zero / cold-start trade-off already covered in the model-serving
tutorial](../ml_system_design/04_model_serving_deployment.md#autoscaling-for-model-serving).
Sizing an instance correctly for average load and then discovering the real traffic is
spiky is precisely the [provisioning-factor
mistake](01_performance_and_scale.md#back-of-the-envelope-capacity-estimation) Part 1
warns against.

## Putting It Together: Why Batching Matters So Much on a GPU

This is the payoff — the piece of GPU hardware understanding that directly explains a
technique already covered elsewhere in this repo. A GPU has thousands of cores organized
into warps waiting to execute the same instruction across many data points *simultaneously*
— if you send it a single request (one sequence to generate, one image to classify), the
vast majority of those cores sit **idle**, because there isn't enough parallel data to fill
them. The GPU's entire value proposition — massive parallel throughput — goes unused by a
workload of one.

**This is precisely why [continuous batching in the vLLM serving
deep-dive](../ml_system_design/06_rag_llm_serving_at_scale.md#deep-dive-llm-serving-internals-vllm-on-triton)
matters as much as it does**: batching multiple independent requests together gives the
GPU's parallel hardware enough simultaneous, independent work to actually saturate its
cores, instead of running mostly-idle on one request at a time. Understanding *this*
section is what turns "batching improves GPU utilization" from a memorized fact into
something you could have derived yourself from the hardware up.

## Quick Self-Check

- Why can't a GPU's 10,000 cores be understood as "10,000 independent tiny CPUs" — what's
  actually different about how they execute code?
- Why does branchy, data-dependent code run poorly on a GPU specifically, mechanically —
  not just "GPUs are bad at branches" as a memorized fact?
- Why does a GPU need physically separate on-board memory instead of just using the CPU's
  system RAM, and why is that the same underlying idea as caching?
- Why does sending a single request to a GPU waste most of its actual compute capacity?
- Why would an inference-only workload be *worse off* paying for an HBM-based
  training-class GPU instead of a GDDR6-based inference GPU like the L4 — what exactly
  would that extra bandwidth and power draw be buying you that you can't use?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Latency-vs-throughput framing (the default, and the one that ties this back to the
  rest of the primer):** "I wouldn't explain CPU vs. GPU as 'GPUs are for AI' — I'd frame
  it as the same latency-versus-throughput axis from earlier, just built into silicon.
  CPUs optimize for finishing one instruction stream fast; GPUs optimize for running the
  same operation across massive parallel data."
- **Mechanism-not-fact framing (good for 'why are GPUs bad at branchy code'):** "I wouldn't
  just say 'GPUs are bad at branches' as a memorized fact — I'd explain warp divergence:
  32 threads in a warp execute the same instruction in lockstep, so a branch forces the
  hardware to run both paths serially with threads masked off. That's a mechanical
  consequence of SIMT, not a vague limitation."
- **Scarcity-drives-technique framing (good for explaining quantization/PagedAttention
  without sounding like a term-dropper):** "I'd connect these back to one root cause — GPU
  memory is small, fast, and physically separate from system RAM. Quantization,
  gradient checkpointing, and PagedAttention are all different answers to that same
  scarcity, not three unrelated clever tricks."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **SIMT (Single Instruction, Multiple Threads)** (n. phrase) — the GPU execution model
  where a warp of threads executes the same instruction simultaneously on different data.
- **warp divergence** (n. phrase) — the performance penalty when threads in a warp take
  different branch paths and the hardware must serialize them instead of running both in
  parallel.
- **HBM (High Bandwidth Memory)** (n.) — memory physically stacked next to a GPU's compute
  die, built for far higher bandwidth than general-purpose system RAM; the memory type on
  training-class GPUs (A100/H100), not on inference-class ones.
- **GDDR6** (n.) — a cheaper, lower-bandwidth, lower-power memory technology used on
  inference-class GPUs (T4, A10, L4); the deliberate trade of bandwidth for cost and
  power efficiency on a workload that doesn't need HBM's throughput.
- **training-class vs. inference-class GPU** (adj. phrase) — a segmentation by what the
  chip's memory/power budget is optimized for, not just raw capability; picking the wrong
  class means paying for a bottleneck-relief the workload can't use.
- **host vs. device** (adj. phrase) — CPU-side (host) versus GPU-side (device) in ML
  tooling; a "host-to-device transfer" is data crossing from system RAM to GPU memory.
- **OOM (out of memory)** (n. phrase, GPU-specific usage) — exhausting a GPU's small,
  precious on-board memory, a distinctly different failure mode from exhausting system RAM.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…discovered hardware that already happened to fit"** — a precise, memorable way to
  explain that GPUs weren't designed for AI, they were repurposed because the workload
  shapes matched.
- **saturate** (v.) — to fully utilize a resource's capacity. *"Batching gives the GPU
  enough parallel work to actually saturate its cores, instead of running mostly idle."*
- **"…is the same underlying constraint, solved from different angles"** — useful for
  showing several techniques (quantization, checkpointing, paging) share one root cause
  rather than listing them as unrelated facts.
- **"…not a software limitation, it's the hardware's execution model"** — a fluent way to
  ground a performance claim in mechanism rather than folklore.

---

**Previous:** [Part 3: Communication & Resilience](03_communication_and_resilience.md)  |  **Next:** [Part 5: Choosing a GPU & Code Optimization](05_gpu_selection_and_code_optimization.md)
