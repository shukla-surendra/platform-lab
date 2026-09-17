# LoRA & QLoRA, Mechanism by Mechanism

Part of the [LLM Engineering Curriculum](00_roadmap.md), Part 3 — Fine-Tuning. Builds on
[Chapter 16](16_fine_tuning_landscape.md)'s PEFT category — this chapter is exactly what
LoRA's inserted "small number of new parameters" actually are, the math behind why they
work, and QLoRA's extension of the same idea, including a real hardware constraint that
directly shapes which projects in this repo use which technique. See also
[`personal_notes_lora_and_peft_alternatives.md`](personal_notes_lora_and_peft_alternatives.md)
for a condensed, standalone quick-reference version of this same material.

## In Plain English

LoRA doesn't touch the model's original weight matrices at all — it leaves them frozen
and adds a small, separate "correction" alongside each one, computed as the product of
two much smaller matrices. Only those two small matrices get trained. The insight making
this work: the *change* a model needs to adapt to a new task tends to be far simpler
(lower "rank," in the linear-algebra sense) than the full complexity of the original
weight matrix — so a much smaller number of parameters is enough to capture it.

## The First-Principles Explanation

### The actual math: low-rank decomposition

For any weight matrix `W` (shape `d × k`) in the frozen base model that LoRA targets,
instead of directly updating `W`, LoRA adds a correction `ΔW`, decomposed as the product
of two small matrices:

```
ΔW = B × A

where:
  A has shape (r × k)   — "down-projects" into a small r-dimensional space
  B has shape (d × r)   — "up-projects" back out to the original d dimension
  r (the "rank")  <<  min(d, k)   — the whole point: r is small, often 8-64,
                                     while d and k can be in the thousands

Effective forward pass through this layer:
  output = W·x + ΔW·x = W·x + B·(A·x)
```

`W` never changes — it stays exactly as the pretrained model had it. Only `A` and `B` are
trained (`W` is frozen). The parameter count for `A` and `B` combined is `r×k + d×r` —
compare against `W`'s own `d×k` parameters: when `r` is small (say 16) and `d`/`k` are in
the thousands, `A`+`B`'s combined size is a tiny fraction of `W`'s — this is the exact
mechanism behind [Chapter 16](16_fine_tuning_landscape.md#deep-dive-why-peft-specifically-matters-for-this-curriculums-no-gpu-constraint)'s
"0.4% of parameters trainable" figure.

### `alpha` — the scaling factor, and why it exists separately from `r`

LoRA's actual contribution to the forward pass is scaled: `output = W·x + (alpha/r)·B·(A·x)`.
`alpha` controls how strongly the learned correction influences the output, independent of
`r` (the rank/capacity of that correction). A common convention (used in this repo's own
config, `lora_alpha=32` with `lora_r=16`) sets `alpha` to roughly `2×r` — worth knowing as
a real, empirically-common starting ratio, not a hard rule.

### Which weight matrices actually get LoRA applied — `target_modules`

LoRA isn't applied to *every* weight in a Transformer — it's applied to specific,
chosen matrices, per [Chapter 10](10_transformer_architecture.md)'s architecture:

```python
# fine_tuning/tinyllama-1.1b-lora/train_tinyllama_lora.py
lora_cfg = LoraConfig(
    r=args.lora_r,
    lora_alpha=args.lora_alpha,
    lora_dropout=args.lora_dropout,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",      # attention's Q/K/V/output projections
        "gate_proj", "up_proj", "down_proj",           # the MLP block's matrices
    ],
    bias="none",
    task_type="CAUSAL_LM",
)
```

This targets essentially every major weight matrix in each Transformer block — both the
attention projections ([Chapter 10](10_transformer_architecture.md#self-attention-the-mechanism-that-lets-tokens-look-at-each-other))
and the MLP's matrices ([Chapter 10](10_transformer_architecture.md#the-mlp-block-per-token-processing-after-attention-mixes-information),
though `TinyLlama`'s SwiGLU-based MLP names them `gate_proj`/`up_proj`/`down_proj` rather
than this curriculum's simpler GELU-MLP naming — same conceptual role). Targeting more
matrices generally captures more of what fine-tuning could change, at the cost of more
trainable parameters — a real, tunable trade-off, not a fixed requirement.

## Grounded in This Repo's Code, End to End

```python
base_model = AutoModelForCausalLM.from_pretrained(args.model_id, torch_dtype=dtype, ...)
base_model.config.use_cache = False
base_model.gradient_checkpointing_enable()

model = get_peft_model(base_model, lora_cfg)
model.print_trainable_parameters()
```

`get_peft_model` (from the `peft` library) performs the actual insertion described above
— it walks `base_model`'s modules, finds every one named in `target_modules`, freezes its
original weight, and attaches a new `A`/`B` pair. `gradient_checkpointing_enable()` is a
separate, complementary memory-saving technique worth naming precisely: it trades
recomputation for memory by *not* storing every intermediate activation during the
forward pass (needed for backprop's chain rule, per
[Chapter 3](03_how_neural_networks_learn.md#step-3-backpropagation--the-chain-rule-applied-systematically)),
instead recomputing them on demand during the backward pass — independent of LoRA itself,
but commonly used alongside it since both are aimed at the same constraint (fitting
training into limited memory).

## Deep-Dive: How QLoRA's Quantization Actually Works

**QLoRA** extends LoRA with one more idea: keep the frozen base model's weights in a
**quantized**, 4-bit format (not the 16/32-bit precision LoRA alone uses) — dramatically
shrinking the base model's memory footprint, while the trainable `A`/`B` LoRA matrices
still train in higher precision on top. Three specific techniques, not just "round to
4 bits":

**1. NF4 (4-bit NormalFloat)** — not generic, evenly-spaced 4-bit quantization. Pretrained
LLM weights are approximately normally distributed, so NF4's 16 possible quantization
levels are placed at the *quantiles* of a standard normal distribution instead of spaced
uniformly — precision gets concentrated where the weight distribution actually has
density. This is specifically why NF4 outperforms plain int4/fp4 for this exact use case
(neural network weights), rather than being a general-purpose 4-bit format.

**2. Double quantization (DQ)** — quantizing in blocks (commonly 64 weights/block) needs a
per-block scaling constant, usually stored in fp32; at that block size, the constants
themselves add roughly 0.5 bits/parameter of overhead on top of the 4 bits already spent.
QLoRA quantizes *those scaling constants too* (in larger blocks, e.g. 256), cutting that
overhead to roughly 0.373 bits/parameter — a second, smaller layer of compression on top
of the first, not a separate technique.

**3. Paged optimizers** — uses NVIDIA unified memory so optimizer state automatically
pages out to CPU RAM during a GPU memory spike (a long sequence, a gradient-checkpointing
recomputation burst) instead of the training run OOM-crashing.

**To be precise about what is and isn't lower precision here, since it's easy to
conflate two separate facts:** the frozen base model's weights genuinely *are*
quantized to lower precision, permanently — each original `bf16` weight gets rounded to
its nearest one of NF4's 16 representable levels, and that rounding is real, lossy, and
irreversible. You cannot recover the original `bf16` value from the stored 4-bit one
afterward. That precision loss is the actual cost QLoRA pays for its memory savings, not
something that gets "undone" later.

Separately, at *compute time*, each forward pass **dequantizes** the needed blocks back
into a `bnb_4bit_compute_dtype` container (typically `bfloat16`) before the actual matmul
runs — not because this recovers any lost precision (it doesn't), but because GPU tensor
cores have fast, well-optimized `bfloat16` matmul kernels, not efficient native 4-bit
ones. The multiply-accumulate arithmetic itself runs at `bfloat16` precision, on an input
that was already degraded by the quantization step. Both facts hold at once: the *stored
weight* is lower precision, permanently; the *arithmetic operation* uses `bfloat16`, on
an already-lossy value.

The LoRA `A`/`B` matrices never go through any of this — they're never quantized at all,
train in full `bfloat16` throughout, and since the base is frozen
(`requires_grad=False`), gradients only ever flow through the adapters, never through the
quantized weights.

Concretely, via `transformers` + `bitsandbytes` + `peft` (the planned shape of
[`fine_tuning/qwen2.5-7b-instruct-l4-lora/`](../../fine_tuning/qwen2.5-7b-instruct-l4-lora/README.md)
— written up below, not yet built):

```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
from peft import prepare_model_for_kbit_training, get_peft_model, LoraConfig
import torch

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",           # NF4, not plain fp4/int4
    bnb_4bit_use_double_quant=True,       # double quantization
    bnb_4bit_compute_dtype=torch.bfloat16, # dequantize-to-compute dtype
)

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct", quantization_config=bnb_config, device_map="auto",
)
model = prepare_model_for_kbit_training(model)  # casts norms to fp32, enables
                                                  # gradient checkpointing
model = get_peft_model(model, lora_cfg)  # same LoraConfig shape as this
                                           # chapter's target_modules section
```

`Qwen2.5-7B-Instruct`'s own weights at `bf16` are `7.6B × 2 bytes ≈ 15.2GB` — too tight on
a single 24GB L4 for plain LoRA (frozen bf16 base + adapter, gradients, activations) to
leave comfortable headroom. NF4 quantization brings the frozen base down to roughly
`≈3.8GB`, freeing the rest of the 24GB for adapter gradients/optimizer state and real
activation memory at a workable batch size — this exact memory math is what
`fine_tuning/qwen2.5-7b-instruct-l4-lora/README.md` already documents as the reason that
project needs QLoRA specifically, not plain LoRA, once it's built.

## Deep-Dive: What Training Produces, and What It's Compatible With

**Q: After QLoRA training finishes, what does `model.save_pretrained(output_dir)` actually
write to disk — a new quantized model, a new bf16 model, or something else?**

A: Neither. It writes only the adapter — `adapter_config.json` (the `LoraConfig`: rank,
alpha, `target_modules`, ...) and `adapter_model.safetensors` containing just the trained
`A`/`B` matrices. The base model, quantized or not, is never re-saved as part of this —
it's a few megabytes, not gigabytes, because `A`/`B` are the only parameters that were
ever trainable in the first place (this chapter's `r×k + d×r` math). Whoever loads this
adapter later is expected to load the base model fresh from its own original source
(`Qwen/Qwen2.5-7B-Instruct` from the Hub) and attach the adapter on top.

**Q: Is the saved `adapter_model.safetensors` itself in NF4, or in bf16?**

A: `bfloat16` (or whatever full precision the adapter trained in) — never NF4. NF4
quantization only ever applied to the *frozen base's* weights; the LoRA `A`/`B` matrices
were never quantized at any point, per the previous section. The "new safetensor weight"
the question asks about is, precisely, full-precision, not a quantized artifact.

**Q: So at inference, does that adapter have to be attached to the NF4-quantized base
(the one it was trained against), or does it work with the original bf16 base too?**

A: **Both work — this is a genuinely independent choice, made separately from how
training happened.** The adapter is just an additive correction,
`output = W·x + (alpha/r)·B·(A·x)`, and it doesn't know or care what `W` is:

- **Reload the base in NF4 again** (`quantization_config=bnb_config`, same as training)
  and attach the adapter — cheapest at inference, matches training exactly, but the
  base's NF4 rounding error is still present in every inference pass, same as it was
  during training.
- **Reload the base in its original, unquantized `bf16`** and attach the *same* adapter —
  no code change needed beyond dropping `quantization_config`; this generally gives
  *better* output quality, since the base no longer carries NF4's rounding error, while
  still getting whatever behavior shift the adapter learned. The one real subtlety: the
  adapter was trained against the *quantized* base's actual forward-pass values, not the
  pristine ones, so there's a small, usually-negligible training/inference mismatch — the
  adapter never actually saw the exact numbers the full-precision base produces. In
  practice, because NF4's error is small and the adapter is a small correction on top,
  this mismatch rarely matters, and swapping to the full-precision base at inference is
  common, legitimate practice, not a hack.
- **Merge the adapter into the base** (`model.merge_and_unload()` in `peft`), producing
  one standalone model instead of a base+adapter pair —
  `W_new = W + (alpha/r)·B·A`, baked directly into the weights. This requires the base to
  be in an addable, unquantized format (`bf16`/`fp32`) first — you don't merge directly
  into a still-4-bit base. The resulting merged model is a completely ordinary bf16
  checkpoint, deployable anywhere, and can itself be quantized *again* afterward with a
  different, inference-oriented technique if a small serving footprint is wanted (e.g.
  GGUF for `llama.cpp`/LM Studio — see
  [`fundamentals/gpu_infrastructure/phase5_llm_serving/13_quantization.md`](../../../fundamentals/gpu_infrastructure/phase5_llm_serving/13_quantization.md))
  — a separate, later, inference-time quantization decision, unrelated to QLoRA's
  training-time one.

**Q: So what was the actual purpose here — quantize in order to go back to the original
afterward, or quantize and keep using the quantized model going forward?**

A: **Neither, as a fixed rule — QLoRA's quantization exists to solve a *training-memory*
problem specifically, and what happens at inference is a completely separate decision
made afterward, based on what inference-time constraints actually are.** If the
deployment target has the same tight memory constraint training did, keep the NF4 base
and pay its small, already-accepted quality cost again at inference. If the deployment
target has more headroom (a bigger GPU, or CPU inference isn't latency-critical), reload
the original bf16 base — or merge — and get better quality output for the same trained
adapter, at the cost of more memory. The quantization decision and the deployment
decision are not the same decision, and nothing about QLoRA forces them to match.

## Q&A: Quantizing Purely to Shrink a Model, With No Fine-Tuning At All

**Q: Is "quantize the model, fine-tune it, then use the quantized one" always the goal
when someone says "quantize a model" — the QLoRA shape from this chapter?**

A: No. That's specifically QLoRA's shape — quantize *in order to make training fit in
memory*, with a LoRA adapter expected to exist afterward. A separate, more common goal
has nothing to do with training at all: take an already fully-trained model and produce a
smaller version of it — same parameter count, fewer bits per parameter — purely to make
it cheaper/faster to serve. This is **post-training quantization (PTQ)**, and no
fine-tuning step happens anywhere in it.

**Q: What's the actual mechanical difference between QLoRA's quantization and PTQ?**

A: QLoRA's NF4 quantization is a *means to a training end* — the base gets quantized,
then a LoRA adapter trains on top of it, and the adapter is the real deliverable. PTQ has
no "on top of it" step: the quantized weights themselves are the final artifact, meant to
be loaded and served exactly as they are, forever, with nothing else attached.

**Q: What techniques are actually used for PTQ?**

A: The full mechanism-level explanation for each of these already lives in
[`fundamentals/gpu_infrastructure/phase5_llm_serving/13_quantization.md`](../../../fundamentals/gpu_infrastructure/phase5_llm_serving/13_quantization.md)
— short version:

- **GPTQ** — quantizes layer by layer using a small calibration dataset, solving for the
  quantized weights that minimize *output* error (not raw rounding error), correcting for
  earlier layers' already-introduced error as it goes. Produces INT4/INT8.
- **AWQ** — identifies the small fraction of high-impact weight *channels* by observing
  activations during calibration, protects those at higher precision, quantizes the rest
  aggressively.
- **FP8** — not a calibration algorithm at all, a native hardware format on H100/H200
  Tensor Cores — the simplest of these to apply, and often the best throughput-per-
  accuracy trade-off on current-gen NVIDIA hardware.
- **SmoothQuant** — a pre-quantization scaling transform that migrates quantization
  difficulty from activation outliers onto weights, typically paired with a
  weight-quantization method on top rather than used alone.
- **GGUF** — not an algorithm, a *file format* (llama.cpp/LM Studio) packaging weights
  already quantized by llama.cpp's own methods (`Q4_K_M`, `Q8_0`, ...) for
  single-machine, CPU/GPU-mixed serving.

**Q: Does `bitsandbytes` (the library QLoRA uses) count as one of these PTQ techniques?**

A: Not typically for production serving. `bitsandbytes` is primarily a fine-tuning-context
tool (QLoRA specifically); GPTQ, AWQ, and FP8 are the ones actually chosen for serving an
already-trained model at scale.

**Q: Since PTQ keeps the same parameter count, is there any training/gradient step
happening during GPTQ/AWQ/SmoothQuant's calibration?**

A: No — that's the defining property, and the reason "no fine-tuning" in the question is
exactly right. Calibration runs a small dataset through the model in inference-only
forward passes to measure activation statistics or output error, then uses that to choose
quantization parameters (scale factors, which channels to protect at higher precision).
No gradients, no backprop, no weight updates via gradient descent anywhere in the
process. Every logical parameter keeps its identity; only its stored bit-width changes.

**Q: So is doing PTQ retraining, or is it literally a tool — feed in a model, get a
smaller model out?**

A: It's a tool, not retraining. Concretely: you run a script or CLI, give it {the
full-precision model checkpoint, optionally a small calibration dataset}, it runs (no
training loop, no epochs, no optimizer, no loss being minimized via gradient descent),
and it writes {a new, smaller model checkpoint} to disk. That new checkpoint is the
literal, final output artifact — not an in-memory conversion you redo every time, for the
calibration-based methods (see the `bitsandbytes` contrast below for the one real
exception to that).

**Q: Walk through GPTQ's actual process step by step.**

A:
1. Load the full-precision (`bf16`/`fp32`) trained model checkpoint.
2. Feed a small calibration dataset (a few hundred to a couple thousand representative
   text sequences — doesn't need to be the original training data, just realistic input)
   through it, one forward pass at a time, capturing each layer's actual input
   activations as they flow through.
3. For each linear layer's weight matrix, in order, solve for the INT4/INT8 weight
   values that minimize *that layer's output error* given the real activations just
   captured — a closed-form/greedy numerical procedure (using an approximation of the
   layer's Hessian), processed column-by-column, carrying forward and compensating for
   the error already introduced by earlier, already-quantized columns.
4. Write the result — quantized weight tensors plus per-group scale factors/zero-points
   — to a new checkpoint directory, tagged in a format inference engines that support
   GPTQ (vLLM, TGI, TensorRT-LLM) know how to load directly.

None of this is gradient descent — it's a numerical fitting procedure over activations
captured from forward passes, run once, producing one fixed output.

**Q: How does AWQ's process differ from that?**

A: Same overall shape (calibration data → forward passes → a new saved checkpoint), but
a different criterion: instead of solving layer-by-layer for minimum output error, AWQ
uses the calibration activations to identify which *channels* of each weight matrix have
outsized impact on the output, protects that small fraction at higher precision (or
rescales them to reduce their quantization error), and quantizes the rest of the matrix
more aggressively. Still purely a forward-pass/statistics-gathering process — no
gradients here either.

**Q: Does FP8 conversion even need a calibration dataset?**

A: Less than GPTQ/AWQ, sometimes not at all. FP8 isn't a calibration algorithm — it's a
hardware number format. The simplest version just computes a per-tensor scale factor
from the weights' own value range (no data needed at all, "static" scaling); a more
careful version runs a small calibration set through the model to pick better per-tensor
or per-channel scale factors ("dynamic"/activation-informed scaling) — but even that is
one lightweight forward-pass pass, nothing resembling a training loop.

**Q: What does actually running one of these tools look like, concretely?**

A: A CLI or a short library call, not a training script:

```bash
# GPTQ, via AutoGPTQ / optimum
optimum-cli quantize gptq \
  --model Qwen/Qwen2.5-7B-Instruct \
  --dataset wikitext2 \
  --bits 4 \
  --output-dir ./qwen2.5-7b-gptq-int4

# GGUF, via llama.cpp -- two steps: convert to GGUF, then quantize it
python convert_hf_to_gguf.py ./Qwen2.5-7B-Instruct --outfile qwen2.5-7b-f16.gguf
./llama-quantize qwen2.5-7b-f16.gguf qwen2.5-7b-Q4_K_M.gguf Q4_K_M
```

Input: a model directory. Output: a new, smaller model file/directory, both cases.

**Q: Does running the quantization tool itself need a GPU, separate from later serving
the quantized model?**

A: Yes, for GPTQ/AWQ — the calibration step runs real forward passes through the
full-precision model, which for a 7B+ model needs GPU memory the same way any inference
does. It's far cheaper than training, though: no backward pass, no optimizer state, no
multi-epoch loop — a single pass over a few hundred to a couple thousand calibration
sequences, typically minutes, not the hours-to-days a real training run takes.

**Q: Is this the same kind of thing as QLoRA's own quantization, mechanically?**

A: Same underlying idea (fewer bits per weight), but a real difference in *when* it
happens and what it produces. GPTQ/AWQ/GGUF tools run once and **persist** a new smaller
checkpoint to disk — you load that file directly from then on, never re-running the
quantization step. `bitsandbytes`' NF4 quantization (what QLoRA uses) is normally applied
**at model-load time, from the original `bf16` checkpoint, every single time** —
`BitsAndBytesConfig(load_in_4bit=True)` re-quantizes on the fly each time you load the
model, rather than reading a pre-quantized file. It's possible to save an NF4-quantized
model explicitly too, but that's not the default workflow the way it is for
GPTQ/AWQ/GGUF, where producing a saved artifact *is* the entire point of running the
tool.

## Deep-Dive: Why QLoRA Isn't What Runs on a MacBook Today

The mechanism above is real and widely used — worth understanding precisely why it
*isn't* what either fine-tuning project in this repo actually runs today:

**The actual constraint**: QLoRA's 4-bit quantization is implemented by the
`bitsandbytes` library, whose custom quantization kernels are built specifically for
NVIDIA CUDA GPUs. `bitsandbytes` has historically had little to no working support for
Apple Silicon's MPS backend — meaning QLoRA, as commonly implemented, simply isn't a
functioning option on a MacBook's GPU today. This is a real, checkable hardware
limitation, not a design preference — it's the direct reason
[`fine_tuning/tinyllama-1.1b-lora/train_tinyllama_lora.py`](../../fine_tuning/tinyllama-1.1b-lora/train_tinyllama_lora.py)
loads the base model at `torch.float16` (via `model_dtype()`, checked against MPS
availability), not 4-bit — plain LoRA on a float16 base model, not QLoRA, is the correct
choice for this hardware.

**What this means practically for a MacBook-based fine-tuning setup**: you get LoRA's
full training-memory advantage (Chapter 16's dramatic reduction, since gradients/optimizer
state still only apply to the small `A`/`B` matrices), but not QLoRA's *additional*
reduction in how much memory the frozen base model itself occupies. For a model in the
hundreds-of-millions-to-low-single-billions-of-parameters range (like `TinyLlama-1.1B`,
or the smaller base model this curriculum's next chapters use), plain LoRA at float16 is
comfortably within a modern MacBook's unified memory — QLoRA's extra squeeze becomes
essential mainly for meaningfully larger base models (7B+), where it isn't available on
MPS regardless.

## Deep-Dive: LoRA's Neighbors in the PEFT Family

LoRA is the dominant PEFT technique (and the only one this repo's own projects use), but
it's worth knowing what else lives in the same category from
[Chapter 16](16_fine_tuning_landscape.md) — each makes a different, more aggressive trade
between "how few parameters get trained" and "how much control that gives you":

| Technique | Basic idea | Relative trainable-parameter count |
|---|---|---|
| **LoRA** | Low-rank matrices added alongside frozen weight matrices (this chapter) | Low |
| **QLoRA** | LoRA + a 4-bit quantized frozen base model (above) | Low (same as LoRA — the reduction is in *base model* memory, not trainable params) |
| **Adapters** (bottleneck adapters) | Small feed-forward modules inserted *between* existing layers, rather than added alongside a weight matrix | Low |
| **Prefix Tuning** | Learn a set of "virtual token" vectors prepended to every layer's input, steering attention without changing any weight matrix at all | Very low |
| **Prompt Tuning** | Similar to prefix tuning, but learns virtual vectors only at the input embedding layer, not injected into every layer | Very low |
| **(IA)³** | Learn per-channel scaling vectors that rescale activations, rather than adding new matrices | Very low |
| **BitFit** | Train *only* the existing bias terms already in the model, nothing new added | Very low |

**The pattern across this whole family**: every one of these answers [Chapter 16](16_fine_tuning_landscape.md)'s
same question — "freeze almost everything, train something small" — differently. LoRA's
specific answer (low-rank matrices alongside existing weights) has become the dominant
default because it hits a strong practical balance: enough capacity to meaningfully shift
behavior (unlike the very-low-capacity methods at the bottom of the table), while still
being dramatically cheaper than full fine-tuning — this repo's own projects' choice of
LoRA specifically, not one of its lower-capacity neighbors, reflects that same trade-off.

### LoRA isn't LLM-specific

Worth knowing explicitly: the low-rank-decomposition idea this chapter explains has
nothing inherently to do with language models — it's a general technique for adapting
*any* large neural network cheaply. It's also widely used for image-generation models
(e.g., Stable Diffusion), where a LoRA adapter can teach a base model a specific visual
style, character, or object, with multiple such adapters swappable on top of the same
frozen base model — the exact same "small correction alongside frozen weights" mechanism
this chapter derives, applied to a completely different architecture and modality.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Higher LoRA rank (`r`) | More capacity to represent the fine-tuning change | More trainable parameters, more memory/compute (though still far less than full fine-tuning) |
| More `target_modules` | Captures more of what full fine-tuning could change | More trainable parameters |
| LoRA (float16 base) on MPS | Actually works on Apple Silicon today | No QLoRA-style further reduction in base-model memory |
| QLoRA (4-bit base) | Meaningfully lower base-model memory, enabling larger models on constrained hardware | Effectively CUDA-only via `bitsandbytes` — not a working option on MPS as of this writing |

## Try It Yourself

- In [`../../fine_tuning/tinyllama-1.1b-lora/train_tinyllama_lora.py`](../../fine_tuning/tinyllama-1.1b-lora/train_tinyllama_lora.py),
  try changing `--lora-r` from 16 to 4, re-run `model.print_trainable_parameters()`, and
  confirm the trainable-parameter count drops roughly in proportion — direct, observed
  confirmation of the `r×k + d×r` formula's linear dependence on `r`.

## Common Misconceptions

- **"LoRA modifies the original model weights, just efficiently."** No — the original
  weights (`W`) are never touched at all; they stay completely frozen. LoRA adds a
  parallel, separate correction (`B×A`) that gets combined with `W`'s output at
  inference/training time.
- **"QLoRA is strictly better than LoRA, so you should always use it if possible."** It's
  a different trade-off (lower base-model memory, at the cost of quantization's own
  precision loss and, currently, CUDA-only tooling) — not a strictly-better upgrade,
  especially given it's not available on MPS at all.
- **"QLoRA quantization means the model computes in 4-bit."** No — 4-bit is a storage
  format for the frozen base's weights only. Every forward pass dequantizes the needed
  blocks back to `bnb_4bit_compute_dtype` (typically `bfloat16`) before the actual matmul
  runs — the memory saved is in how the weights sit at rest, not in the precision compute
  happens at.
- **"A higher LoRA rank always produces a better fine-tuned model."** More capacity isn't
  automatically better — per [Chapter 4](04_hyperparameter_tuning.md)'s general
  hyperparameter-tuning reasoning, an unnecessarily high rank just adds trainable
  parameters (and overfitting risk on small datasets) without a guaranteed quality gain.

## Practice Questions

1. Write out the shapes of `A` and `B` for a weight matrix `W` of shape `2048×2048` with
   LoRA rank `r=16`, and compute the parameter-count reduction versus fine-tuning `W`
   directly.
2. Why does `alpha` exist as a setting separate from `r`, rather than just using a larger
   `r` to increase the correction's influence?
3. Explain, precisely, why QLoRA's memory advantage over plain LoRA is about the *frozen
   base model*, not about the trainable LoRA matrices themselves — and why that means
   QLoRA's benefit scales with base model size.
4. Why does NF4 place its quantization levels at the quantiles of a normal distribution
   instead of spacing them evenly — and what specifically would go wrong (in terms of
   quantization error) if it used evenly-spaced levels instead for typical LLM weights?
5. Double quantization compresses the *scaling constants*, not the weights themselves.
   Given a block size of 64 weights per scaling constant, sketch out why that constant's
   own overhead (~0.5 bits/parameter before DQ) is worth compressing further at all.
6. After QLoRA training, `save_pretrained` writes only the adapter, not a new base model.
   Explain precisely why this is enough to fully reproduce the fine-tuned behavior later,
   given what `A`/`B` actually represent (`ΔW`, not `W` itself).
7. Two people fine-tune the identical base model with QLoRA, save identical adapters, then
   deploy differently — one reattaches the adapter to an NF4-quantized base, the other to
   the original bf16 base. Will their outputs be identical? Explain what specifically
   would differ, and why the difference is generally small rather than large.

## Key Terms

- **Low-rank decomposition**: representing a matrix update as the product of two much
  smaller matrices, exploiting the idea that the needed update has much lower complexity
  ("rank") than the full weight matrix.
- **Rank (`r`)**: the shared inner dimension of LoRA's `A`/`B` matrices — the capacity
  knob for how much the correction can represent.
- **`alpha`**: the scaling factor controlling how strongly the LoRA correction influences
  the frozen base model's output.
- **`target_modules`**: which specific weight matrices in the model get a LoRA adapter
  attached.
- **Gradient checkpointing**: trading recomputation for memory by not storing every
  forward-pass activation, recomputing them during backprop instead.
- **QLoRA**: LoRA combined with a 4-bit quantized frozen base model, implemented via
  `bitsandbytes` — effectively CUDA-only, not currently functional on Apple Silicon MPS.
- **NF4 (4-bit NormalFloat)**: QLoRA's quantization data type — levels placed at the
  quantiles of a standard normal distribution rather than evenly spaced, matching the
  actual distribution of pretrained LLM weights.
- **Double quantization (DQ)**: quantizing the per-block scaling constants that
  quantization itself introduces, cutting their overhead from ~0.5 to ~0.373
  bits/parameter.
- **Paged optimizers**: NVIDIA unified-memory-backed automatic paging of optimizer state
  to CPU RAM during a GPU memory spike, avoiding an OOM crash.
- **Adapter checkpoint**: what `save_pretrained` actually writes after LoRA/QLoRA
  training — just `adapter_config.json` + the `A`/`B` weights, never a copy of the base
  model. Requires the original base to be loaded separately before it can be used.
- **`merge_and_unload()`**: bakes a trained adapter directly into the base model's
  weights (`W_new = W + (alpha/r)·B·A`), producing one standalone checkpoint instead of a
  base+adapter pair. Requires an unquantized (`bf16`/`fp32`) base to merge into.
- **Compute dtype**: the higher precision (e.g. `bfloat16`) a quantized weight is
  dequantized *to* before each matmul — quantization saves storage, not compute
  precision.
- **Adapters (bottleneck adapters)**: small feed-forward modules inserted between
  existing layers, a different PEFT approach than LoRA's alongside-the-weight-matrix
  correction.
- **Prefix / Prompt Tuning**: learning virtual token vectors (prepended at every layer,
  or just at the input embedding) to steer behavior, without adding to or modifying any
  weight matrix.
- **(IA)³ / BitFit**: even lower-capacity PEFT methods — learned per-channel activation
  scaling, and training only existing bias terms, respectively.
