#!/usr/bin/env bash
# One-time: clone + build llama.cpp's C++ binaries (llama-quantize, llama-cli).
# Separate from requirements.txt's Python deps, which only cover the HF->GGUF
# conversion script (pure Python, no build needed for that step).
set -euo pipefail

cd "$(dirname "$0")/.."
VENDOR_DIR="vendor/llama.cpp"

if [ -d "$VENDOR_DIR" ]; then
  echo "$VENDOR_DIR already exists -- leaving it alone. Delete it to force a rebuild."
  exit 0
fi

mkdir -p vendor
git clone --depth 1 https://github.com/ggml-org/llama.cpp "$VENDOR_DIR"

cmake -S "$VENDOR_DIR" -B "$VENDOR_DIR/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$VENDOR_DIR/build" --config Release -j "$(nproc)" --target llama-quantize llama-cli

echo "Built: $VENDOR_DIR/build/bin/llama-quantize, $VENDOR_DIR/build/bin/llama-cli"
