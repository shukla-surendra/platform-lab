# make setup     - one-time: clone + build llama.cpp's binaries (needs git, cmake, a C/C++ toolchain)
# make convert   - download SmolLM2-135M, convert to full-precision (f16) GGUF
# make quantize  - produce Q8_0 / Q4_K_M / Q4_0 GGUF files from the f16 one
# make compare   - print file sizes, then run the same prompt through all four
# make all       - convert + quantize + compare, in order (assumes setup already ran)
# make clean     - remove models/ (downloaded/converted/quantized files); vendor/ (the
#                  built llama.cpp) is left alone so re-running doesn't mean rebuilding it

.PHONY: setup convert quantize compare all clean

setup:
	bash scripts/setup.sh

convert:
	bash scripts/convert.sh

quantize:
	bash scripts/quantize.sh

compare:
	bash scripts/compare.sh

all: convert quantize compare

clean:
	rm -rf models
