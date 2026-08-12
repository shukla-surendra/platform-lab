# Quantization: Buying Back Memory and Bandwidth, Trading Accuracy

Part of [Phase 5 — LLM Serving & Inference](../README.md#phase-5-llm-serving-inference).
Builds on [`03_gpu_architecture.md`'s HBM bandwidth section](../phase2_gpu_fundamentals/03_gpu_architecture.md#hbm-why-gpu-memory-bandwidth-not-just-capacity-is-the-real-budget)
— read that first if the claim "quantization speeds up decode by moving fewer bytes, not
by doing less math" doesn't already make sense. This chapter is the deep version of what
[`tools-and-frameworks.md`'s quantization tooling section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tools-and-frameworks.md#quantization-tooling)
names in passing, plus the direct answer to "what is quantization?" asked alongside LM
Studio in the session that started this track — see
[`23_lmstudio_and_local_inference.md`](../local_and_prototyping/23_lmstudio_and_local_inference.md)
for quantization's role in single-machine local inference specifically.

## Clarify

Quantization means representing a model's weights (and sometimes activations) using
fewer bits per number than the format they were trained in — trading numerical precision
for less memory used and, per the HBM-bandwidth mechanism above, faster inference. It is
**not** a training technique by default (that's a separate, related idea — quantization-
*aware* training) — the common case discussed here is **post-training quantization**:
take an already-trained model and convert its weights to a lower-precision format before
serving it.

**The one-sentence framing that survives an interview follow-up**: quantization isn't
free compression — it's a deliberate trade of numerical range/precision for memory
footprint and bandwidth, and the real engineering question is always "how much accuracy
does this specific model lose at this specific precision, on this specific workload,"
not "is quantization good."

## Core Concepts

### The precision ladder

| Format | Bits | Bytes/param | Notes |
|---|---|---|---|
| FP32 | 32 | 4 | Full precision, rarely used for serving — the training-era default, wasteful for inference |
| FP16 / BF16 | 16 | 2 | The common training and default-serving precision. BF16 has FP32's exponent range (better for training stability); FP16 has more mantissa bits (slightly more precision, smaller range) |
| FP8 | 8 | 1 | Natively accelerated on H100/H200 Tensor Cores — a real hardware format, not software-emulated. Two sub-variants: E4M3 (more precision, less range) and E5M2 (more range, less precision), chosen per-tensor based on which matters more for that tensor |
| INT8 | 8 | 1 | Integer quantization — requires a scale factor (and often a zero-point) to map back to the real value range; more mature tooling than FP8 on older (pre-H100) hardware |
| INT4 | 4 | 0.5 | The aggressive end — roughly 8x smaller than FP32, or 4x smaller than FP16. Meaningful accuracy risk without careful calibration |

**Direct connection to the memory math already established**: the 500B-parameter,
~1TB-at-FP16 example from
[`tutorial.md`'s worked example](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tutorial.md#deep-dive-sizing-the-cluster-a-worked-example)
becomes ~500GB at FP8/INT8, or ~250GB at INT4 — directly changing the GPU-count math
that worked example walks through (2 nodes of `p5.48xlarge` at FP16 could become 1 node
at FP8, a real infrastructure-cost decision, not just an accuracy one).

### Why quantization isn't just "round every number down"

Naive uniform rounding of every weight to a lower precision produces measurably worse
models than the techniques actually used in production, because not all weights matter
equally and not all tensors have the same value distribution. The real tools address
this:

- **GPTQ (Generative Pre-trained Transformer Quantization)** — quantizes layer by layer,
  using a small calibration dataset to solve for the quantized weights that minimize the
  *output* error of that layer (not just the weight-rounding error in isolation),
  correcting for the error introduced by already-quantized earlier weights as it goes.
  Produces INT4/INT8 weights, widely supported as an input format across vLLM, TGI, and
  TensorRT-LLM per
  [`tools-and-frameworks.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tools-and-frameworks.md#quantization-tooling).
- **AWQ (Activation-aware Weight Quantization)** — starts from a different observation:
  not all weight *channels* matter equally, and the ones that matter most can be
  identified by looking at the *activations* that flow through them during calibration
  (not the weights alone). AWQ protects a small fraction of high-impact weight channels
  at higher precision (or scales them to reduce quantization error) while quantizing the
  rest aggressively — the "activation-aware" part of the name is the actual mechanism,
  not marketing.
- **FP8** — unlike GPTQ/AWQ, this isn't a calibration algorithm; it's a *hardware
  numeric format*. Converting to FP8 is comparatively simple (choose per-tensor scale
  factors) precisely because the format itself, run on H100/H200 Tensor Cores, is
  natively accelerated — the "free-est" of the quantization options on current-generation
  NVIDIA hardware, which is why
  [`tools-and-frameworks.md`](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/tools-and-frameworks.md#quantization-tooling)
  calls it "frequently the best throughput-per-accuracy-loss trade-off."
- **bitsandbytes** — a lighter-weight library, common in research/fine-tuning contexts
  (notably QLoRA fine-tuning, where the *base* model is quantized while LoRA adapters
  train in higher precision on top of it) — less commonly the production serving choice
  at scale, as already noted in `tools-and-frameworks.md`.
- **SmoothQuant** — worth naming as a third calibration philosophy alongside GPTQ/AWQ:
  observes that activation outliers (not weight outliers) are often the harder problem
  for INT8 quantization specifically, and migrates quantization difficulty from
  activations to weights via a per-channel scaling transform applied *before*
  quantization — a preprocessing step rather than a quantization algorithm itself,
  often paired with a separate weight-quantization method on top.

### GGUF — the format underneath LM Studio and llama.cpp

A different axis worth naming separately: **GGUF** is not a quantization *algorithm*, it's
a *file format* (successor to GGML) used by llama.cpp and, by extension, LM Studio — it
packages quantized weights (produced by llama.cpp's own quantization methods, labeled
like `Q4_K_M`, `Q5_K_S`, `Q8_0`) plus metadata into one portable file, optimized for fast
loading and CPU/GPU-mixed inference on a single machine rather than for distributed
serving-engine formats like the ones vLLM/TensorRT-LLM consume. The `Q4_K_M`-style naming
encodes: bit-width (4), a quantization scheme variant (`K`), and a size/quality preset
(`M` = medium) — see
[`23_lmstudio_and_local_inference.md`](../local_and_prototyping/23_lmstudio_and_local_inference.md)
for how this shows up as an actual dropdown choice in LM Studio's model picker.

## Reference: the two things quantization actually buys

```
                    Quantize weights: FP16 → FP8/INT4
                              │
              ┌───────────────┴───────────────┐
              ▼                                 ▼
     Less HBM capacity used            Less HBM bandwidth needed
     (fit a bigger model on            per forward pass
      fewer/smaller GPUs)              (faster decode — see the
              │                         memory-bound mechanism in
              ▼                         03_gpu_architecture.md)
     Fewer GPUs needed                          │
     → direct AWS cost reduction,                ▼
       revisited as an ongoing lever        Higher tokens/sec at
       in aws-production-architecture.md    the same batch size
```

Both benefits are real and separate — a team optimizing purely for "fit the model" and a
team optimizing purely for "serve faster at the same footprint" are both legitimately
using quantization, for different reasons, and a strong answer names which one a given
decision is actually optimizing for.

## Trade-offs

| Precision | Memory/bandwidth win | Accuracy risk | Where it's used |
|---|---|---|---|
| BF16/FP16 | Baseline (no reduction from training precision) | None (this is usually the reference point) | Default serving precision absent a specific reason to go lower |
| FP8 | 2x over FP16 | Low, especially on H100/H200 with native support | Increasingly the production default on current-gen NVIDIA hardware |
| INT8 (GPTQ/AWQ) | 2x over FP16 | Low-to-moderate, calibration-dependent | Mature choice on pre-H100 hardware without native FP8 |
| INT4 (GPTQ/AWQ) | 4x over FP16 | Moderate — real, measurable degradation on some tasks, especially reasoning-heavy ones | Aggressive cost/footprint-constrained deployments, local inference (LM Studio) |

## Failure Modes to Raise Proactively

- **Treating "quantization" as one technique with one accuracy cost** — the actual answer
  depends on precision level, calibration method, and task; a strong response names which
  axis is being discussed rather than a single blanket claim.
- **Assuming FP8 is "free" because it's hardware-accelerated** — the acceleration is real,
  but per-tensor format choice (E4M3 vs. E5M2) and calibration still matter for accuracy;
  "natively supported" and "zero accuracy cost" are different claims.
- **Re-litigating the quantization decision only at launch** — as
  [`aws-production-architecture.md`'s cost management section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#cost-management)
  already names, the right precision trade-off point shifts as hardware and tooling
  mature; treating it as revisited rather than one-time is itself the correct answer to a
  "how do you keep this efficient over time" follow-up.

## Make It Yours

- Next time a model needs to be served, name the actual decision explicitly: is the
  constraint "doesn't fit in available GPU memory" (favors going as low-precision as
  accuracy allows) or "fits fine but latency/cost needs improving" (favors FP8 first,
  the lowest-risk lever, before reaching for INT4)?
- If using LM Studio locally (per
  [`23_lmstudio_and_local_inference.md`](../local_and_prototyping/23_lmstudio_and_local_inference.md)),
  compare a `Q4_K_M` and a `Q8_0` build of the same model on the same prompt — the
  quality/speed trade-off is directly observable, not just theoretical.

## Practice Questions

1. A team quantizes a model from FP16 to INT4 and sees a 4x memory reduction but only a
   1.3x throughput improvement, not 4x — why isn't the throughput gain proportional to
   the memory gain?
2. Why does AWQ specifically look at activations during calibration, when it's the
   *weights* that end up quantized?
3. A model quantized to FP8 for prefill-heavy (compute-bound) traffic and a model
   quantized to FP8 for decode-heavy (memory-bound) traffic — does FP8 help both cases
   equally? Why or why not?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "Quantization represents weights with fewer bits — FP16 down
to FP8 or INT4 — which buys two separate things: the model fits on fewer/smaller GPUs,
and inference gets faster because decode is memory-bandwidth-bound, so moving fewer bytes
per token directly speeds up generation. The cost is accuracy, and the real engineering
work is calibration — GPTQ and AWQ both use a small dataset to minimize the *output*
error the quantization introduces, not just round every number down uniformly."

**The follow-up-proof version**: be ready to explain why FP8 on H100/H200 is qualitatively
different from INT4 on older hardware — one is a native hardware format with dedicated
Tensor Core support, the other is quantization-plus-dequantization happening around
otherwise-FP16 compute — and connect precision choice back to whether the actual
constraint is memory capacity or memory bandwidth.

**Vocabulary builder**: *post-training quantization* (converting an already-trained
model, vs. quantization-aware training), *calibration dataset* (the small sample used to
tune quantization parameters to minimize real output error), *per-channel / per-tensor
scaling* (applying different scale factors to different slices of a tensor rather than
one global scale, a common accuracy-preserving refinement).
