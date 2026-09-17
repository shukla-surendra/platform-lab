#!/usr/bin/env bash
# Side-by-side comparison across all four precision levels: file size, then the same
# prompt run through each via llama-cli, so the size/quality/speed trade-off from
# 13_quantization.md's precision ladder is directly observable, not just theoretical.
set -euo pipefail

cd "$(dirname "$0")/.."
CLI_BIN="vendor/llama.cpp/build/bin/llama-cli"
PROMPT="${1:-The capital of France is}"

echo "=== file sizes ==="
ls -lh models/smollm2-135m-f16.gguf models/smollm2-135m-Q8_0.gguf \
       models/smollm2-135m-Q4_K_M.gguf models/smollm2-135m-Q4_0.gguf

for level in f16 Q8_0 Q4_K_M Q4_0; do
  echo
  echo "=== $level ==="
  "$CLI_BIN" -m "models/smollm2-135m-${level}.gguf" \
    -p "$PROMPT" -n 40 --no-display-prompt 2>&1 | tail -5
done
