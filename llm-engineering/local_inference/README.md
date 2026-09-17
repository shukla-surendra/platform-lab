# local_inference

Part of [llm-engineering](../README.md) — local LLM/vision-model experimentation,
distinct from that project's other tracks in one specific way: everything here runs
against models already pulled/running on this machine (mainly via
[Ollama](https://ollama.com)), not something trained or fine-tuned in this repo. `uv`-
managed (`pyproject.toml`/`uv.lock`, Python 3.12+); `ollama-chatbox/` is its own separate
npm project. (Moved here from a former top-level `local_llms/` — same content,
renamed to fit alongside `from_scratch/`, `fine_tuning/`, `base_models/`,
`quantization/`.)

## `ollama-chatbox/`

A minimal React chat UI talking to a local Ollama server — streaming
responses, model picker populated from whatever's pulled. See its own
[README](./ollama-chatbox/README.md) for setup (`npm install && npm run dev`).

## `notebooks/`

Exploration notebooks against the local Ollama REST API (`http://localhost:11434`),
run in order:

| Notebook | What it covers |
|---|---|
| [`ollama_exploration.ipynb`](./notebooks/ollama_exploration.ipynb) | The raw REST API and the official `ollama` Python client — listing/loading models, generate, chat. |
| [`gemma4_exploration.ipynb`](./notebooks/gemma4_exploration.ipynb) | Deep dive on `gemma4:latest` (8B, Q4_K_M) — chat, `think` reasoning mode, tool calling, and vision (reading the receipts in `notebooks/receipts/`). |
| [`ocr_exploration.ipynb`](./notebooks/ocr_exploration.ipynb) | Receipts through `deepseek-ocr:latest` (3.3B, OCR-specialist) — free-form OCR and prompted structured extraction (merchant, date, line items, total) as JSON. |
| [`ocr_comparison.ipynb`](./notebooks/ocr_comparison.ipynb) | `gemma4` vs `deepseek-ocr` head-to-head on the same receipts with identical prompts. |

`notebooks/receipts/` — the sample receipt images all three OCR/vision
notebooks read from.

## `deepfake-detector/`

Three standalone smoke-test scripts, each trying a different pretrained
Hugging Face deepfake-classifier checkpoint against a face image (default is
just a non-face smoke-test image to confirm the pipeline runs):

```bash
uv run python deepfake-detector/deepfake_detector_v1_test.py path/or/url/to/face.jpg
```

| Script | Checkpoint |
|---|---|
| `deepfake_detector_v1_test.py` | `prithivMLmods/deepfake-detector-model-v1` (SigLIP) |
| `deepfake_detector_v2_test.py` | `prithivMLmods/Deep-Fake-Detector-v2-Model` |
| `deepfake_detector_wvolf_test.py` | `Wvolf/ViT_Deepfake_Detection` |

## `vit/`

Same Vision Transformer feature extraction (`google/vit-base-patch16-224-in21k`,
same test image), run through two different backends for comparison:
`vit_pytorch_test.py` (PyTorch) and `vit_flax_test.py` (Flax/JAX).
