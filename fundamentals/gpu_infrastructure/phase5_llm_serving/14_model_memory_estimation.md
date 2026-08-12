# Model Memory Estimation: The Full Budget, Not Just the Weights

Part of [Phase 5 — LLM Serving & Inference](../README.md#phase-5-llm-serving-inference).
Closes out Phase 5. [`tutorial.md`'s worked example](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tutorial.md#deep-dive-sizing-the-cluster-a-worked-example)
already computed one term of this budget (weights: params × bytes/param). This chapter is
the complete formula — every term that actually competes for HBM, for both inference and
training, since the two have genuinely different budgets and conflating them produces a
wrong sizing estimate.

## Clarify

"How much memory does this model need" has no single correct answer without first
answering "for what" — serving one request, serving many concurrent requests, or
training. Each adds different terms to the budget, and the terms that dominate shift
depending on the answer. A sizing estimate that only counts model weights (a common
shortcut) is reliably wrong the moment concurrent traffic or training is involved — this
chapter is the complete accounting, term by term, so an estimate can be defended line by
line rather than asserted as a single number.

## Core Concepts

### The inference memory budget, complete

```
Total HBM needed (inference) =
    Model weights
  + KV cache (grows with concurrent requests × context length)
  + Activation memory (comparatively small at inference — no gradients)
  + Framework/runtime overhead (CUDA context, workspace buffers — usually
    a few GB, worth budgeting explicitly rather than ignoring)
```

- **Model weights** — `params × bytes/param`, the term
  [`tutorial.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tutorial.md)
  already uses, directly reduced by
  [`13_quantization.md`](13_quantization.md)'s precision choice.
- **KV cache** — the term this track has referenced repeatedly without the full formula
  until now:

  ```
  KV cache size = 2 × batch_size × seq_length × num_layers
                  × num_kv_heads × head_dim × bytes_per_element

  The leading 2 is for K and V separately (one cache for keys, one for
  values). num_kv_heads matters specifically because architectures using
  grouped-query attention (GQA) or multi-query attention (MQA) use FEWER
  KV heads than attention heads — a direct, deliberate memory-reduction
  choice made at the model-architecture level, independent of anything
  this track's serving-infra chapters control. A model published with
  GQA has a smaller KV cache footprint per token than an equivalently
  sized model using full multi-head attention, for the same batch size
  and context length — worth checking which attention variant a given
  model actually uses before sizing a deployment around it.
  ```

  **Why this is the term that actually breaks naive sizing estimates**: weights are
  fixed once a model is chosen; KV cache scales with *traffic* (batch size) and *context
  length* — both operational variables that change after deployment, not architectural
  constants. A deployment sized correctly for weights alone can still OOM under real
  concurrent load or long-context requests if KV cache headroom wasn't budgeted
  separately — the exact incident shape
  [`aws-production-architecture.md`'s monitoring section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#monitoring-the-metrics-that-actually-matter-here)
  names KV cache occupancy tracking as guarding against ("a leading indicator before it
  becomes an OOM incident").

### The training memory budget — genuinely different terms, genuinely larger

Training adds terms inference never has, and removes the assumption that memory is
roughly proportional to model size alone:

```
Total HBM needed (training, per GPU, before any parallelism sharding) =
    Model weights (same as inference)
  + Gradients (same size as weights — one gradient per parameter)
  + Optimizer states (the term that dominates — see below)
  + Activations (retained for the backward pass — NOT comparable to
    inference's small activation footprint, because inference discards
    activations after each layer's forward pass, while training must
    keep them until backprop uses them)
```

**Optimizer states are the term most sizing intuition misses entirely.** Adam (the
standard optimizer for LLM training) maintains two additional per-parameter values —
momentum and variance — each the same size as the parameter itself. In FP32 (the common
choice for optimizer state precision, even when weights themselves train in mixed
precision), this alone is:

```
Optimizer states (Adam, FP32) = 2 × params × 4 bytes = 8 bytes/param

Compare against inference's weights-only footprint at FP16 (2 bytes/param):
  Training's optimizer-state term ALONE is 4x larger than inference's
  entire weight footprint, before even counting the weights, gradients,
  or activations training also needs.
```

This is the concrete, numeric reason training a given model needs meaningfully more GPU
memory than serving it — not a vague "training needs more resources" claim, but a
specific term (optimizer state) that inference has no equivalent of at all.

### Putting it together: a full worked comparison

For a 70B-parameter model, comparing inference and training footprints at the weights
level alone already diverges sharply once every term is counted:

| Term | Inference (FP16 weights) | Training (FP16 weights, FP32 Adam states) |
|---|---|---|
| Weights | 70B × 2 bytes = 140GB | 70B × 2 bytes = 140GB |
| Gradients | — (not applicable) | 70B × 2 bytes = 140GB |
| Optimizer states (Adam) | — (not applicable) | 70B × 8 bytes = 560GB |
| KV cache / activations | Scales with batch × context (variable) | Activations retained for backprop — also substantial, workload-dependent |
| **Rough total** | **~140GB + variable KV cache** | **~840GB+ before activations** |

This is *why* training infrastructure sizing (Phase 7's subject) and inference
infrastructure sizing (this folder's subject) are genuinely different exercises, not the
same math applied twice — the dominant term isn't even the same category of thing.

## Deep-Dive: why this table is the mechanism behind FSDP/ZeRO, not just a training fact

This chapter doesn't implement FSDP/ZeRO (that's
[`21_fsdp_deepspeed_zero.md`](../phase7_advanced_training_infra/21_fsdp_deepspeed_zero.md)'s
job), but it supplies the exact reason those systems exist: since optimizer states are
the single largest term in the training budget — larger than weights and gradients
combined, in the Adam/FP32 case above — **sharding optimizer states across GPUs** (rather
than replicating them on every GPU, the naive data-parallel default) is the single highest-
leverage memory optimization available for large-model training. ZeRO's stage numbering
(Stage 1: shard optimizer states, Stage 2: also shard gradients, Stage 3: also shard
weights) is literally ordered by which term of this exact budget table gets attacked
first — Stage 1 alone already claws back the largest term.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Size inference deployment for weights + peak expected KV cache | Correct, defensible capacity plan | Requires knowing (or bounding) real traffic's concurrent batch size and max context length in advance |
| Size inference deployment for weights only, ignore KV cache | Simpler estimate | Reliably wrong under real concurrent traffic — the exact OOM-incident shape named above |
| FP32 Adam optimizer states (training) | Numerically stable, the safe default | The single largest memory term in the entire training budget — first target for any memory optimization |
| 8-bit optimizer states (bitsandbytes, training) | Meaningfully smaller optimizer-state footprint | A training-time accuracy/stability trade-off, distinct from inference-time quantization's trade-off (different risk profile, different context) |

## Failure Modes to Raise Proactively

- **Sizing an inference deployment from weights alone** — the single most common mistake
  this chapter exists to prevent; KV cache is traffic-dependent and has to be budgeted
  with real expected concurrency and context length, not treated as a rounding error.
- **Assuming a model architecture's KV cache formula uses full multi-head attention
  without checking** — GQA/MQA models have meaningfully smaller KV cache footprints per
  token; using the full-MHA formula on a GQA model overestimates memory needs and can lead
  to over-provisioning.
- **Comparing a training memory estimate against an inference one without separating the
  terms** — as the worked comparison shows, the categories of memory pressure are
  different (optimizer states vs. KV cache), so "how much memory does this model need"
  answered with one number, without specifying which workload, is not a complete answer.

## Make It Yours

- For a model you've worked with or plan to deploy, work through this chapter's inference
  formula by hand: weights (from its parameter count and chosen precision) plus KV cache
  at a specific assumed batch size and context length — turn the formula into one real,
  concrete number rather than leaving it abstract.
- Check whether that model uses GQA/MQA (most current open-weight LLMs do) before
  applying the KV cache formula — confirms whether the "fewer KV heads" reduction applies.

## Practice Questions

1. Why does Adam's optimizer state alone (in FP32) outweigh the entire inference-time
   weight footprint (in FP16) for the same model, and what does that imply about where a
   training-memory optimization effort should focus first?
2. Two models have the same parameter count, but one uses grouped-query attention and the
   other uses full multi-head attention — which one supports a larger concurrent batch
   size at the same context length and GPU memory budget, and why?
3. A team sizes an inference deployment using only the model's weight footprint and hits
   OOM errors under production load that never appeared in testing — what's the most
   likely missing term, and why would testing (likely lower concurrency, shorter
   contexts) not have caught it?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "Memory sizing has to name which workload it's for — inference
needs weights plus a KV cache that scales with concurrent traffic and context length, not
just a fixed number. Training needs weights, gradients, and optimizer states — and Adam's
optimizer states alone, in FP32, are typically the single largest term in the entire
training budget, larger than the weights themselves. That's the concrete reason training
needs meaningfully more memory than serving the same model, and it's the exact reason
ZeRO/FSDP shard optimizer states first — that's the highest-leverage term to attack."

**The follow-up-proof version**: be ready to write out the KV cache formula from memory
and explain why GQA/MQA models have smaller footprints — naming `num_kv_heads` as a
model-architecture choice, not a serving-infrastructure lever, is the detail that shows
real understanding rather than a memorized formula.

**Vocabulary builder**: *optimizer state* (Adam's momentum and variance terms, one pair
per parameter, the dominant training-memory term), *grouped-query attention (GQA)* /
*multi-query attention (MQA)* (attention variants using fewer KV heads than query heads,
directly shrinking KV cache size), *activation memory* (memory retained for the backward
pass during training — near-zero at inference, substantial during training).
