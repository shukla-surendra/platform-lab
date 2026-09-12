# NVIDIA Training GPUs (T4 / V100 / L4 / A100)

**Category:** hardware — accelerator selection for model training/fine-tuning

## What it is

The GPU is what turns "how many FLOPs does training need" into "how many wall-clock hours does
it take" — the same training job (same params, same tokens) runs at wildly different speeds and
costs depending on which of these four cards it lands on. They cover the range a small/medium
model project is actually likely to hit: T4 is the free-tier default, V100 is the "priced but
not premium" tier, L4 is a newer mid-tier card that's easy to mistake for V100's replacement,
and A100 is the card that removes the memory ceiling the other three run into.

Without knowing the specs, a project either overpays (renting A100 for something a T4 could do)
or stalls (trying to fit a 1B-param model's optimizer state into a 16GB card that doesn't have
the VRAM). The specs below are what make that decision quantitative instead of a guess.

## What it's used for

- Estimating how long a training/fine-tuning run will take before starting it, from
  `training_time ≈ (6 × params × tokens) / (GPU peak FLOPS × achieved utilization)`.
- Deciding whether a model even *fits* on a given card: VRAM has to hold weights + gradients +
  optimizer state + activations. Full-precision Adam needs roughly ~16 bytes/param (4 weights +
  4 grads + 8 for Adam's two fp32 moment buffers) before activations are counted; mixed
  precision (fp16/bf16) roughly halves the weights/grads portion.
- Explaining why two GPUs with near-identical peak TFLOPS (V100 and L4, below) can still produce
  different training times in practice — peak compute isn't the only variable; memory bandwidth
  determines how fast data reaches the compute units, and small-batch LLM training has plenty of
  bandwidth-bound steps (attention softmax, layernorm, elementwise ops), not just matmuls.

## Alternatives / comparison

| GPU | Architecture | FP16/BF16 Tensor Core (dense) | Memory | Bandwidth | Typical availability |
|---|---|---|---|---|---|
| T4 | Turing (2018) | ~65 TFLOPS | 16 GB GDDR6 | ~320 GB/s | Colab Free default |
| V100 | Volta (2017) | ~125 TFLOPS | 16/32 GB HBM2 | ~900 GB/s | Colab Pro ($10/mo) historically |
| L4 | Ada Lovelace (2023) | ~121 TFLOPS | 24 GB GDDR6 | ~300 GB/s | Cloud (GCP/AWS), some Colab tiers |
| A100 | Ampere (2020) | ~312 TFLOPS | 40/80 GB HBM2 | ~1555/2039 GB/s | Colab Pro+, on-demand cloud |

Key relationships, not obvious from the numbers alone:
- **V100 and L4 are near-tied on peak compute** (~125 vs ~121 TFLOPS) despite being 6 years
  apart — but V100 has 3x the memory bandwidth (900 vs 300 GB/s). A workload that's
  bandwidth-bound (small batch, attention-heavy) will run meaningfully slower on L4 than on V100
  *despite* the similar peak FLOPS; a workload that's compute-bound (large batch, big matmuls)
  will land close to parity. This is why quoting "TFLOPS" alone to compare two GPUs is
  misleading without also checking bandwidth.
- **A100 isn't just faster — it removes a ceiling.** Its 40-80 GB of VRAM is what lets a
  ~1B-param model's Adam optimizer state (~16 bytes/param before activations) fit at all without
  aggressive tricks (gradient checkpointing, 8-bit optimizers, LoRA/QLoRA). T4/V100/L4's
  16-24 GB caps out well before that, independent of how much time you're willing to spend.
- **RTX 4090 (consumer, not in the table above)** has 24 GB VRAM like L4 but no cloud meter
  running — cost becomes electricity instead of $/hr billing, and there's no forced session
  timeout (unlike Colab Free) pushing the trainable model size back down.

## Usage — sizing an SLM training run

Worked example: estimating a 350M-parameter run on L4 when the only known reference point is a
Colab-Pro figure that names a *price tier*, not a GPU.

1. Identify what GPU the reference number likely used. Colab Pro's $10/mo tier has historically
   meant V100-class access (Pro+ is the tier that adds A100).
2. Compare peak Tensor Core FLOPS: L4 (~121 TFLOPS) is close to V100 (~125 TFLOPS) — parity here
   alone would suggest similar wall-clock time.
3. Compare memory bandwidth: L4 (300 GB/s) is 3x lower than V100 (900 GB/s) — at 350M-param
   scale, plenty of the training step is bandwidth-bound (attention softmax, layernorm), so
   FLOPS parity doesn't guarantee time parity.
4. Resulting estimate: L4 should land slower than the V100 baseline but faster than T4 (which
   has both lower compute *and* similar-to-L4 bandwidth), with the exact number depending on
   batch size — larger batch pushes the run toward compute-bound (closer to the V100 number),
   smaller batch pushes it toward bandwidth-bound (further from it).

General cost math that applies across all four cards:
`cost = ($/hr for the GPU) × (training hours)`, and `training hours = FLOPs needed ÷ achieved
throughput` — so a quoted "$X per run" figure is really that hourly rental rate multiplied by
however many hours the FLOPs/bandwidth tradeoff above works out to.

Caveat that applies to all size/cost tables built this way: instructional/demo training runs use
a small, fixed token budget to produce *a* working model in a reasonable time — not the
Chinchilla-optimal ratio (~20 tokens/param) a real base model would be pretrained with. A model
sized to "fit in an 8-16 hour A100 run" at demo-token-budget would need far more time at a
production-scale token count.
