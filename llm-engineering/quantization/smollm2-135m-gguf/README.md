# SmolLM2-135M — Post-Training Quantization to GGUF

Part of [llm-engineering](../../README.md)'s **quantization track** — a hands-on
companion to the theory already written up in
[`fundamentals/gpu_infrastructure/phase5_llm_serving/13_quantization.md`](../../../fundamentals/gpu_infrastructure/phase5_llm_serving/13_quantization.md)
and the Q&A in
[`docs/llm-engineering/17_lora_and_qlora.md`](../../docs/llm-engineering/17_lora_and_qlora.md#qa-quantizing-purely-to-shrink-a-model-with-no-fine-tuning-at-all).
Those docs explain *what* post-training quantization (PTQ) is and *why* GPTQ/AWQ/FP8/GGUF
exist; this project is where you actually run one — GGUF, via `llama.cpp` — end to end,
on the same `HuggingFaceTB/SmolLM2-135M` checkpoint
[`serving/smollm2-135m-base-serving`](../../serving/smollm2-135m-base-serving)
already serves unquantized.

## Why GGUF, and why this model

- **GGUF/`llama.cpp` runs on CPU** — no CUDA required, unlike GPTQ/AWQ (which need a real
  GPU for calibration) or `bitsandbytes`/QLoRA (CUDA-only, per
  [Chapter 17](../../docs/llm-engineering/17_lora_and_qlora.md)'s MacBook section). This
  is the one PTQ path that actually runs on this machine today, checked live: no
  `nvidia-smi`, no CUDA, `x86_64` Linux (WSL2).
- **SmolLM2-135M** — the smallest model already used anywhere in this repo (`~270MB` at
  `fp16`), so the whole convert → quantize → compare loop takes minutes, not hours, and
  every step is inspectable without a long wait.

## What you'll actually do

```
HuggingFaceTB/SmolLM2-135M (fp16, HF format)
              │  convert_hf_to_gguf.py  (pure Python — no quantization yet)
              ▼
   smollm2-135m-f16.gguf                       (~270MB, full precision)
              │  llama-quantize  (the actual quantization step)
      ┌───────┼────────────┐
      ▼       ▼             ▼
   Q8_0     Q4_K_M         Q4_0        (smaller, more aggressive, left to right)
```

This is exactly the "give it a model, get a smaller model out" process described in
[Chapter 17's Q&A](../../docs/llm-engineering/17_lora_and_qlora.md#qa-quantizing-purely-to-shrink-a-model-with-no-fine-tuning-at-all)
— no training loop anywhere in it. `llama-quantize` here doesn't even use a calibration
dataset (unlike GPTQ/AWQ) — GGUF's `Q4_K_M`-style k-quants compute per-block scale
factors directly from the weights themselves, no forward pass required at all, which is
part of why this is the fastest PTQ path to actually try by hand.

## Setup

Needs `git`, `cmake`, and a C/C++ toolchain (`build-essential` on this machine) to build
`llama.cpp`'s binaries once — separate from the Python deps below, which only cover the
HF→GGUF conversion script.

```bash
cd quantization/smollm2-135m-gguf
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make setup      # clones + builds llama.cpp into vendor/llama.cpp (one-time, a few minutes)
```

## Run it

```bash
make convert    # downloads SmolLM2-135M from the Hub, writes models/smollm2-135m-f16.gguf
make quantize   # produces models/smollm2-135m-Q8_0.gguf, -Q4_K_M.gguf, -Q4_0.gguf
make compare    # prints file sizes, then runs the same prompt through f16/Q8_0/Q4_K_M/Q4_0
                # side by side so the size/quality/speed trade-off is directly observable
```

`make all` runs every step above in order. `make clean` removes `models/` (the
downloaded/converted/quantized files) without touching the built `llama.cpp` in
`vendor/`, so re-running the experiment doesn't mean rebuilding it.

## What to actually look at

- **File sizes** (`ls -lh models/`) — should land roughly at the precision-ladder ratios
  from `13_quantization.md`'s table: `Q8_0` ≈ half of `f16`, `Q4_K_M`/`Q4_0` ≈ a quarter.
- **Output quality** — same prompt through all four; at 135M parameters (already a small,
  low-capacity model), expect the accuracy cost of aggressive quantization to be *more*
  visible than it would be on a 7B+ model — a real, directly-observable illustration of
  why quantization risk is model-size- and task-dependent, not a fixed universal cost.
- **Load time / tokens-per-second** — printed by `llama-cli`'s own stats — the smaller
  files should load and generate faster on CPU, the practical payoff side of the
  trade-off.

## Next steps, if you want to go further

- Try `Q5_K_M` or `Q2_K` (more k-quant variants `llama-quantize --help` lists) to see
  where quality actually falls off a cliff for this model.
- Compare against `bitsandbytes`' load-time NF4 quantization
  ([Chapter 17](../../docs/llm-engineering/17_lora_and_qlora.md)) on a machine with a CUDA
  GPU, to feel the difference between "quantize once, save a file" (this project) and
  "quantize every time you load, from the original checkpoint" (QLoRA's approach).
- GPTQ/AWQ themselves need a CUDA GPU for calibration and aren't set up here — a natural
  follow-on project once one's available, same theory, different tool.
