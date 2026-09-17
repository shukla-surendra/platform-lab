# serving

Part of [llm-engineering](../README.md)'s **serving track** — every project here loads
an already-trained checkpoint and exposes it over an API. No training, no fine-tuning,
no adapters. Two genuinely different approaches live side by side, merged into one track
because both answer the same question ("how do I actually run and query this model")
rather than being two stages of a pipeline:

| Project | Serves | Variant | Stack | Port |
|---|---|---|---|---|
| [`tinyllama-1.1b-base-serving/`](tinyllama-1.1b-base-serving/) | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | Original, unmodified | Hand-rolled FastAPI | `8002` |
| [`smollm2-135m-base-serving/`](smollm2-135m-base-serving/) | `HuggingFaceTB/SmolLM2-135M` | Base (no chat template) | Hand-rolled FastAPI | `8003` |
| [`smollm2-1.7b-base-serving/`](smollm2-1.7b-base-serving/) | `HuggingFaceTB/SmolLM2-1.7B` | Base (no chat template) | Hand-rolled FastAPI | `8007` |
| [`vllm-smollm2-135m/`](vllm-smollm2-135m/) | `HuggingFaceTB/SmolLM2-135M-Instruct` | Instruction-tuned | vLLM, OpenAI-compatible | `8004` |
| [`vllm-tinyllama-1.1b/`](vllm-tinyllama-1.1b/) | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | Chat-tuned | vLLM, OpenAI-compatible | `8005` |
| [`vllm-qwen2.5-7b-instruct/`](vllm-qwen2.5-7b-instruct/) | `Qwen/Qwen2.5-7B-Instruct` | Instruction-tuned | vLLM, OpenAI-compatible | `8006` |
| [`vllm-qwen3-30b-a3b-multi-gpu/`](vllm-qwen3-30b-a3b-multi-gpu/) | `Qwen/Qwen3-30B-A3B` (MoE) | Instruction-tuned | vLLM, multi-GPU | — planned, not yet built |

## `*-base-serving/` — hand-rolled FastAPI, original checkpoint

One small `api_server.py` per project (~100 lines, no framework beyond FastAPI +
`transformers`), always serving the **original, unmodified author checkpoint** — no
LoRA adapter, no training. For any project whose checkpoint is a true base model (no
chat template — `smollm2-135m-base-serving/`, `smollm2-1.7b-base-serving/`), the server
does **plain-text completion only**: it will not behave like an assistant, and will keep
generating past what looks like a complete answer — that's the point, showing what
pretraining alone produces, before any instruction-tuning or fine-tuning is applied. See
each project's own `docs/MODEL_DETAILS.md` for architecture/training details, all
verified directly against the checkpoint's own `config.json` and the model's official
card, not recalled from memory.

## `vllm-*/` — OpenAI-compatible, typically the instruction-tuned sibling

Each project auto-selects a backend: CUDA vLLM when available, an MLX/Metal route on
Apple Silicon, and a CPU-only Transformers fallback otherwise — see
[`vllm-smollm2-135m/docs/VLLM_SERVING_GUIDE.md`](vllm-smollm2-135m/docs/VLLM_SERVING_GUIDE.md)
for the fullest write-up of vLLM internals, GPU memory/scheduling, tuning, and
troubleshooting, shared conceptually across all four projects here.

**`vllm-tinyllama-1.1b/` and `tinyllama-1.1b-base-serving/` serve the same underlying
model family on purpose** — the vLLM project serves the chat-tuned checkpoint, the
FastAPI project serves the base one, on different ports, so both variants of the same
model can be queried side by side and compared directly.

## Why this is one track and not two

Both halves answer "how do I run and query an already-trained checkpoint," never
"how do I train or adapt one" — that's what keeps this track distinct from
[`../fine_tuning/`](../fine_tuning/) and [`../from_scratch/`](../from_scratch/). The
split between the two *approaches* within this track (hand-rolled vs. vLLM) is about
serving technology and which checkpoint variant (base vs. instruct) each is meant to
demonstrate, not about a different underlying goal.
