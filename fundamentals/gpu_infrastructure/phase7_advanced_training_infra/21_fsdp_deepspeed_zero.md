# FSDP, DeepSpeed, and ZeRO: Sharding the Training Memory Budget, Stage by Stage

Part of [Phase 7 — Advanced Distributed Training Infra](../README.md#phase-7-advanced-distributed-training-infra).
Builds directly on
[`14_model_memory_estimation.md`](../phase5_llm_serving/14_model_memory_estimation.md)'s
training memory budget (weights + gradients + optimizer states) and
[`06_nccl_and_collective_communication.md`](../phase3_gpu_networking/06_nccl_and_collective_communication.md)'s
reduce-scatter/all-gather operations — this chapter is where those two chapters combine
into the actual mechanism ZeRO and FSDP use.

## Clarify

[`07_distributed_training_serving.md`](../../system_design_foundation/01_ml_system_design/07_distributed_training_serving.md)
already covers data/model/pipeline parallelism at the strategy level. This chapter goes
one level deeper into a specific, extremely consequential technique within data
parallelism: **standard data parallelism replicates the full training memory budget —
weights, gradients, AND optimizer states — on every single GPU**, even though each GPU
only ever needs its own shard of that state at any given instant. ZeRO (Zero Redundancy
Optimizer) and FSDP (Fully Sharded Data Parallel) are the mechanism that removes that
redundancy — this chapter is exactly how.

## Core Concepts

### The redundancy standard data parallelism accepts, stated numerically

Recall [`14_model_memory_estimation.md`'s worked comparison](../phase5_llm_serving/14_model_memory_estimation.md#putting-it-together-a-full-worked-comparison):
for a 70B model, Adam optimizer states alone are ~560GB (FP32). In standard data
parallelism across, say, 8 GPUs, **all 8 GPUs each hold a full, identical copy** of that
560GB — 8 × 560GB = 4.48TB of optimizer-state memory across the group, to store what is
fundamentally *the same 560GB of information* eight times over. This is the exact
redundancy ZeRO's name refers to eliminating.

### ZeRO's three stages, mapped directly onto the memory budget's three terms

Each stage shards one additional term from the training budget across the data-parallel
group, instead of replicating it:

```
ZeRO Stage 1 — shard OPTIMIZER STATES only
  Each GPU holds: full weights, full gradients, 1/N of optimizer states
  Removes the single largest term from 14_model_memory_estimation.md's
  table — for the 70B example, this alone cuts the ~560GB optimizer-
  state term to ~70GB per GPU (at N=8), the highest-leverage single
  change available, which is why it's Stage 1 and not Stage 3.

ZeRO Stage 2 — also shard GRADIENTS
  Each GPU holds: full weights, 1/N of gradients, 1/N of optimizer states
  Removes the second-largest term (gradients, same size as weights).

ZeRO Stage 3 — also shard WEIGHTS
  Each GPU holds: 1/N of weights, 1/N of gradients, 1/N of optimizer states
  Removes the last remaining redundant term. This is the stage that
  makes FSDP's name literal — weights themselves are "fully sharded,"
  not just gradients/optimizer state.
```

**The trade each additional stage makes, precisely**: every stage beyond 1 removes more
redundant memory, but requires MORE communication to reassemble the full parameter (or
gradient) a GPU needs at the moment it's actually used in the forward/backward pass —
this is not a free lunch, and the mechanism for that reassembly is exactly the
collectives from
[`06_nccl_and_collective_communication.md`](../phase3_gpu_networking/06_nccl_and_collective_communication.md).

### The actual mechanism: reduce-scatter and all-gather, not a new primitive

This is the direct payoff of naming reduce-scatter and all-gather as separate operations
in [`06_nccl_and_collective_communication.md`](../phase3_gpu_networking/06_nccl_and_collective_communication.md#the-collective-operations-precisely-defined)
rather than treating all-reduce as the only collective worth knowing:

```
FSDP / ZeRO Stage 3, one training step, per layer:

1. Before this layer's forward pass:
   ALL-GATHER — each GPU holds only 1/N of this layer's weights;
   all-gather temporarily reconstructs the FULL layer weights on every
   GPU (just for the duration this layer needs them)

2. Forward pass runs using the full (temporarily gathered) weights

3. Full weights are immediately discarded/freed after use — this is
   why peak memory stays bounded despite reconstructing full weights
   layer by layer, rather than accumulating them

4. Backward pass computes gradients using the same gather-compute-
   discard pattern

5. After backward pass, this layer's gradients exist in full on every
   GPU (from standard backprop) — REDUCE-SCATTER sums them across GPUs
   AND immediately shards the result, so each GPU ends up owning only
   its 1/N shard of the SUMMED gradient, never holding the full summed
   gradient at once

6. Each GPU updates ONLY its 1/N shard of weights using ONLY its 1/N
   shard of optimizer state — the update step itself never needs the
   full parameter tensor
```

**Why reduce-scatter specifically, not all-reduce, at step 5**: an all-reduce would give
every GPU the full summed gradient (exactly what standard data parallelism does, and
exactly the redundancy ZeRO is removing) — reduce-scatter does the same summing but
immediately discards everything except each GPU's own shard, which is precisely why this
operation, not all-reduce, is the one that actually enables the memory savings. This is
the mechanism-level answer to a question left open in
`06_nccl_and_collective_communication.md`'s introduction of the term.

### DeepSpeed vs. FSDP — same idea, two implementations

- **DeepSpeed** — Microsoft's library, the original implementation of ZeRO (Stages 1-3),
  plus additional features like ZeRO-Offload/ZeRO-Infinity (offloading sharded state to
  CPU RAM or NVMe when even sharded GPU memory isn't enough — the training-side sibling
  of the inference-side offload escape valve already named in
  [`tools-and-frameworks.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tools-and-frameworks.md#deepspeed-inference-deepspeed-mii)).
- **FSDP (Fully Sharded Data Parallel)** — PyTorch's own native implementation of the same
  underlying idea (specifically ZeRO Stage 3's full sharding), built into PyTorch's
  distributed package rather than a separate library dependency. The practical
  distinction most teams actually weigh: FSDP's tighter integration with the rest of the
  PyTorch ecosystem (no separate library's abstractions to learn) vs. DeepSpeed's longer
  track record and additional features (offload tiers, more configuration knobs) at
  extreme scale.

## Deep-Dive: why sharding stays within the data-parallel group, and how this composes with TP/PP

An important scoping detail this chapter's diagrams have left implicit: ZeRO/FSDP shard
across the **data-parallel** dimension — GPUs holding *different data batches* but
conceptually the *same model*. This is a different axis entirely from tensor parallelism
(splitting one layer's computation across GPUs, per
[`03_gpu_architecture.md`](../phase2_gpu_fundamentals/03_gpu_architecture.md#deep-dive-why-tensor-parallelism-stays-intra-node))
or pipeline parallelism (splitting layers across GPUs). A real large-scale training setup
typically composes all of these simultaneously — this is "3D parallelism," referenced
without detail in
[`07_distributed_training_serving.md`](../../system_design_foundation/01_ml_system_design/07_distributed_training_serving.md):
TP within a node (NVLink-fast, per this track's Phase 2), PP across node groups, and
FSDP/ZeRO sharding applied *within* the data-parallel replicas of that TP+PP
configuration — three different sharding decisions, three different communication
patterns, layered on top of each other, each solving a genuinely different piece of the
overall memory-and-compute problem.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| ZeRO Stage 1 (optimizer states only) | Removes the single largest redundant term, minimal extra communication | Weights and gradients still fully replicated — meaningful memory still unshared |
| ZeRO Stage 3 / FSDP (full sharding) | Maximum memory reduction — trains models that wouldn't fit any other way | Most communication overhead (all-gather every layer, every forward AND backward pass) — a real throughput cost, not free |
| ZeRO-Offload/Infinity (CPU/NVMe offload) | Trains models that don't fit even with full GPU sharding | Meaningfully slower — CPU RAM/NVMe bandwidth is far below HBM, the same bandwidth-hierarchy argument as `03_gpu_architecture.md`, now applied to offload rather than on-GPU memory |

## Failure Modes to Raise Proactively

- **Assuming more sharding (higher ZeRO stage) is always better** — as shown above, each
  additional stage trades more communication for less memory; a model that already fits
  comfortably at Stage 1 gains nothing from Stage 3 except unnecessary all-gather
  overhead on every layer.
- **Confusing ZeRO/FSDP sharding with tensor parallelism** — both "split something across
  GPUs," but ZeRO shards *state* (weights/gradients/optimizer) across data-parallel
  replicas of the same model, while TP splits *computation* within a single logical model
  replica; conflating them in an interview answer is a real, checkable gap.
- **Not accounting for reduce-scatter/all-gather traffic when sizing interconnect
  requirements for FSDP training** — this traffic happens every layer, every step, and
  needs the same NVLink/RDMA quality reasoning from Phase 3, not just "training needs a
  fast network" as an unexamined assumption.

## Make It Yours

- Walk through the six-step forward/backward trace above out loud, naming which specific
  NCCL collective (from `06_nccl_and_collective_communication.md`) is used at each step —
  the exercise that turns "FSDP shards things" into a mechanism you could defend under a
  follow-up question.
- Given a model and GPU count you're familiar with, estimate (using
  `14_model_memory_estimation.md`'s formula) how much memory ZeRO Stage 1 alone would
  reclaim per GPU, before assuming Stage 3 is necessary.

## Practice Questions

1. Why does ZeRO's stage numbering start with optimizer states, not weights, when weights
   are conceptually "the model" and optimizer states feel like an implementation detail?
2. Why does the all-gather step in FSDP's forward pass need to happen again during the
   backward pass, rather than reusing the weights gathered during the forward pass?
3. A team composes TP=8 (intra-node) with FSDP sharding within each data-parallel
   replica — what's actually being sharded by each mechanism, and why don't they conflict?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "Standard data parallelism replicates the full training memory
budget — weights, gradients, optimizer states — on every GPU, even though each GPU only
needs its own shard at any instant. ZeRO removes that redundancy in three stages,
sharding optimizer states first (the largest term), then gradients, then weights — FSDP
is PyTorch's native implementation of the same idea. The mechanism is reduce-scatter to
shard gradients after backprop and all-gather to temporarily reconstruct full weights
right before each layer needs them, trading extra communication for the memory that's no
longer redundantly held."

**The follow-up-proof version**: be ready to explain why reduce-scatter, not all-reduce,
is the operation at the gradient-sharding step — all-reduce would recreate exactly the
redundancy being removed — and be ready to place ZeRO/FSDP correctly on the "which axis
does this shard" map alongside TP and PP rather than treating all three as interchangeable
"parallelism."

**Vocabulary builder**: *sharding* (splitting state so each GPU holds only a fraction,
distinct from replication), *3D parallelism* (composing data, tensor, and pipeline
parallelism simultaneously, each along a different axis), *offload* (moving sharded state
to a slower tier — CPU RAM or NVMe — when even full GPU-memory sharding isn't enough).
