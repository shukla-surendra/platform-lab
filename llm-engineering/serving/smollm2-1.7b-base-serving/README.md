# SmolLM2-1.7B — Original Base Checkpoint, Served Standalone

Part of [llm-engineering](../../README.md)'s **base-models track**, sibling to
[`../smollm2-135m-base-serving/`](../smollm2-135m-base-serving/) — same idea, the
flagship-sized member of the SmolLM2 family instead of the smallest one. Serves the
**original, unmodified** `HuggingFaceTB/SmolLM2-1.7B` base checkpoint — no LoRA adapter,
no fine-tuning — as its own FastAPI endpoint, own port (`8007`), so all three SmolLM2
variants in this repo can run and be queried side by side.

## Important: plain-text completion only, no chat template

Same situation as the 135M sibling, confirmed directly against this checkpoint's own
`tokenizer_config.json` (no `chat_template` field) — see
[`docs/MODEL_DETAILS.md`](docs/MODEL_DETAILS.md). Send it raw text to continue, not a
question expecting an assistant-style answer.

## Running this locally: check your RAM first

At 1.7B parameters, this is a genuinely bigger load than the 135M sibling — **check
`free -h` before running it**:

| Precision | Weights alone | Notes |
|---|---|---|
| `float32` (CPU default) | ~6.8GB | `--cpu-dtype float32` (default) |
| `float16` (CPU, opt-in) | ~3.4GB | `--cpu-dtype float16` — halves memory, costs CPU inference speed/precision |
| `float16` (CUDA/MPS) | ~3.4GB | Automatic — GPU path always uses `float16`, the `--cpu-dtype` flag has no effect |

This project's own dev machine has only ~3.3GB free RAM at the time of writing (checked
via `free -h`) — **not enough for the `float32` default**, and tight even for
`float16`. If you're on a similarly memory-constrained machine, either free up RAM first,
run this on a machine with more available, or accept `float16`'s quality/speed trade-off
as the only realistic CPU option:

```bash
CPU_DTYPE=float16 bash scripts/serve.sh
```

## Quickstart

```bash
cd serving/smollm2-1.7b-base-serving
uv run api_server.py                      # float32 on CPU by default -- see RAM note above
# or: uv run api_server.py --cpu-dtype float16
```

```bash
curl -X POST http://127.0.0.1:8007/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "The capital of France is", "max_new_tokens": 40}'
```

`GET /health` reports the model ID, device, dtype actually loaded, and confirms no
adapter/chat template is present.

## Original model details

- **Model**: [`HuggingFaceTB/SmolLM2-1.7B`](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B)
- **Original authors**: Hugging Face's SmolLM team — see the model card and the
  [SmolLM2 paper](https://arxiv.org/abs/2502.02737) for full pretraining details, which
  this repo did not perform.
- **License**: Apache 2.0.
- **Architecture**: `LlamaForCausalLM`, confirmed via its `config.json` — same family as
  [`../smollm2-135m-base-serving/`](../smollm2-135m-base-serving/) and
  [`../tinyllama-1.1b-base-serving/`](../tinyllama-1.1b-base-serving/), a genuinely
  different (wider, shallower) shape than either — see
  [`docs/MODEL_DETAILS.md`](docs/MODEL_DETAILS.md) for the exact numbers.

**Full writeup**: see [`docs/MODEL_DETAILS.md`](docs/MODEL_DETAILS.md) for the complete
architecture, pretraining data/hardware/cost (including the one real compute-cost figure
the SmolLM2 paper actually states — this is the model it's about), benchmarks, and known
limitations.
