#!/usr/bin/env bash
# The actual quantization step: takes the f16 GGUF from convert.sh and produces three
# lower-precision versions via llama.cpp's own k-quant methods. No calibration dataset,
# no forward passes -- scale factors are computed directly from the weights per block.
set -euo pipefail

cd "$(dirname "$0")/.."
QUANTIZE_BIN="vendor/llama.cpp/build/bin/llama-quantize"
SRC="models/smollm2-135m-f16.gguf"

if [ ! -f "$SRC" ]; then
  echo "$SRC not found -- run 'make convert' first."
  exit 1
fi

for level in Q8_0 Q4_K_M Q4_0; do
  echo "=== quantizing to $level ==="
  "$QUANTIZE_BIN" "$SRC" "models/smollm2-135m-${level}.gguf" "$level"
done

ls -lh models/smollm2-135m-*.gguf
