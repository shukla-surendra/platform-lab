# SmolLM2-1.7B — Real, Verified Model Details

Every fact in this doc was pulled directly from the model's own real
[model card](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B), its `config.json`/
`tokenizer_config.json` on the Hugging Face Hub, and the team's own technical report
([arXiv:2502.02737](https://arxiv.org/abs/2502.02737)) — not recalled from memory, not
assumed. Same sourcing standard as
[`../../smollm2-135m-base-serving/docs/MODEL_DETAILS.md`](../../smollm2-135m-base-serving/docs/MODEL_DETAILS.md).

## Architecture — verified against the checkpoint's own `config.json`

```
architectures: LlamaForCausalLM
hidden_size: 2048
num_hidden_layers: 24
num_attention_heads: 32
num_key_value_heads: 32
intermediate_size: 8192
vocab_size: 49152
max_position_embeddings: 8192
chat_template: NONE — confirmed absent from tokenizer_config.json
```

Same architecture family (`LlamaForCausalLM`) and same tokenizer/vocab size (`49152`) as
[`../../smollm2-135m-base-serving/`](../../smollm2-135m-base-serving/), but a genuinely
different shape: `hidden_size=2048` (vs. 135M's `576`) across only `24` layers (vs. 135M's
`30`) — wider and *shallower* relative to its width than the smallest sibling, not simply
"the same model, scaled up uniformly." `num_attention_heads == num_key_value_heads == 32`
means this checkpoint uses standard multi-head attention, not grouped-query attention
(GQA) — worth naming since GQA is common in this size class elsewhere.

## Pretraining — from the official [model card](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B#training) and the [technical report](https://arxiv.org/abs/2502.02737)

- **11 trillion tokens** — not 2T like the 135M sibling; the flagship model was trained on
  a genuinely larger token budget, using a mix of
  [`FineWeb-Edu`](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu),
  [`DCLM`](https://huggingface.co/datasets/mlfoundations/dclm-baseline-1.0),
  [`The Stack`](https://huggingface.co/datasets/bigcode/the-stack), plus curated
  mathematics and coding datasets.
- **Hardware**: 256× H100 GPUs — 4x the 135M model's 64× H100 cluster.
- **Training framework**: [`nanotron`](https://github.com/huggingface/nanotron).
- **Precision**: bfloat16.

### The one real compute-cost figure the paper actually states — and it's about this model

Unlike the 135M writeup (where no source states a cost or duration at all), the SmolLM2
paper gives an explicit number, and it's specifically about **this** model. Verbatim from
the paper's introduction:

> "Such on-the-fly rebalancing is a promising approach for large-scale training runs
> which can be sufficiently costly (**around 1e23 FLOPs, or $250,000 USD worth of GPU
> compute for SmolLM2**)"

That `$250,000` / `~1×10²³ FLOPs` figure is anchored to **SmolLM2-1.7B specifically** —
the paper's flagship model — not the 135M or 360M variants, which get no cost/duration
figure at all anywhere in the paper.

**Sanity-check against the `6ND` FLOPs approximation** (same method used for the 135M
sibling's estimate):

```
FLOPs ≈ 6 × N × D  =  6 × 1.7e9 × 11e12  ≈  1.12e23 FLOPs
```

This lands right next to the paper's own stated `~1e23` — a real, useful confirmation
that the simple `6ND` approximation tracks an actual disclosed figure closely, which is
also why it's a reasonable method to fall back on for the 135M model, where no official
number exists at all (see that project's own `MODEL_DETAILS.md`).

**Training duration is still not stated anywhere** — the paper gives cost/FLOPs, not
wall-clock time. Using the same MFU-range approach as the 135M writeup, but now against
256 GPUs instead of 64:

```
256 × 989 TFLOPs/s (H100 SXM peak, BF16) ≈ 2.53e17 FLOPs/s aggregate peak

At 50% MFU: 1.12e23 / (2.53e17 × 0.50) ≈ 886,000s ≈ 10.3 days
At 20% MFU: 1.12e23 / (2.53e17 × 0.20) ≈ 2,213,000s ≈ 25.6 days
```

**Estimate: roughly 10–26 days** — again a derived estimate from public specs and the
`6ND` approximation, not an official figure. Large training runs at this scale typically
land toward the middle-to-lower end of the MFU range (30-40%) due to sustained
multi-week reliability/checkpointing overhead, which would put this run around 13–17
days — still an estimate, not a verified fact.

## Benchmarks — real, from the official model card (base model, zero-shot unless noted)

| Metric | SmolLM2-1.7B | SmolLM2-135M (for scale) |
|---|---|---|
| HellaSwag | **68.7** | 42.1 |
| ARC (Average) | **60.5** | 43.9 |
| PIQA | **77.6** | 68.4 |
| MMLU-Pro | 19.4 | — (135M card reports plain MMLU cloze: 31.5, not directly comparable) |
| CommonsenseQA | **43.6** | 33.9 |
| TriviaQA | **36.7** | 4.1 |
| Winogrande | **59.4** | 51.3 |
| OpenBookQA | **42.2** | 34.6 |
| GSM8K (5-shot) | **31.0** | 1.4 |

The gap is largest exactly where you'd expect from
[`17_lora_and_qlora.md`](../../../docs/llm-engineering/17_lora_and_qlora.md)'s
scaling discussion and this repo's own fine-tuning observations
([`smollm2-135m-dolly-lora/docs/BEFORE_AFTER_COMPARISON.md`](../../../fine_tuning/smollm2-135m-dolly-lora/docs/BEFORE_AFTER_COMPARISON.md)):
**`GSM8K` (grade-school math, genuinely compositional reasoning) jumps from 1.4 → 31.0**,
a far larger relative gain than the general knowledge/commonsense benchmarks — consistent
with reasoning-heavy tasks being the most parameter-count-sensitive, not just the most
fine-tuning-sensitive.

Evaluated using [`lighteval`](https://github.com/huggingface/lighteval), per the model
card, same tooling as the 135M sibling's numbers.

## Known limitations (from the model card, verbatim reasoning)

- Primarily English — content in other languages is not reliably supported.
- "The generated content may not always be factually accurate, logically consistent, or
  free from biases present in the training data" — the model card's own explicit framing.
- Should be used as an assistive tool, not a definitive information source.
- **Same base-model caveat as the 135M sibling**: no instruction-following training at
  all — plain-text completion will continue generating past a "complete" answer rather
  than stopping, exactly as observed live with the 135M checkpoint via this repo's own
  `api_server.py` (see `../../smollm2-135m-base-serving/README.md`'s Quickstart output).
