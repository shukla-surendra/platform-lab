#!/usr/bin/env bash
# Downloads HuggingFaceTB/SmolLM2-135M's HF-format snapshot, then converts it to a
# full-precision (f16) GGUF file -- no quantization happens in this step, purely a
# format conversion. convert_hf_to_gguf.py needs a local directory, not a bare Hub id.
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p models

python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('HuggingFaceTB/SmolLM2-135M', local_dir='models/smollm2-135m-hf')
"

python3 "vendor/llama.cpp/convert_hf_to_gguf.py" \
  models/smollm2-135m-hf \
  --outfile models/smollm2-135m-f16.gguf \
  --outtype f16

ls -lh models/smollm2-135m-f16.gguf
