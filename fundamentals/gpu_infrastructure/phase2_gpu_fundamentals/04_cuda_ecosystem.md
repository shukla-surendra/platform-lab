# The CUDA Ecosystem: What's Actually Underneath vLLM, PyTorch, and Every GPU Command You Run

Part of [Phase 2 — GPU Fundamentals](../README.md#phase-2-gpu-fundamentals). Builds directly
on [`03_gpu_architecture.md`](03_gpu_architecture.md) — this chapter names the actual
software layers that sit between a Python `model.forward()` call and the SM/Tensor-Core
hardware that chapter opened up.

## Clarify: the confusion this chapter resolves

"CUDA" gets used loosely to mean at least four different things in casual conversation —
the driver, the toolkit/compiler, the math libraries, and "the GPU working at all." Each
is a genuinely separate piece of software with a separate versioning scheme, and version
mismatches between them are one of the most common real-world "why won't this container
even start" failures in GPU infrastructure work. This chapter names each layer precisely
enough that a version-mismatch incident (a very real, very common on-call page) can be
diagnosed by layer, not guessed at.

## Core Concepts

### The layers, bottom to top

```
Hardware            GPU die: SMs, Tensor Cores, HBM (03_gpu_architecture.md)
   │
NVIDIA Driver        Kernel module (nvidia.ko) + userspace driver library.
                      Installed once per host, tied to a GPU generation's
                      minimum-supported version. `nvidia-smi` is a driver-level
                      tool — it works even with no CUDA toolkit installed.
   │
CUDA Toolkit          nvcc (compiler), the CUDA Runtime API, headers. What a
                      developer installs to *build* GPU code. Has its own
                      version (e.g. CUDA 12.4), which must be <= what the
                      installed driver supports — not the other way around.
   │
Math / comms          cuBLAS (dense linear algebra), cuDNN (NN primitives:
libraries             convolution, normalization, activation kernels), NCCL
                      (multi-GPU collective communication — Phase 3's subject).
                      These are what PyTorch/TensorFlow actually call for the
                      heavy lifting; they are NOT reimplemented by the
                      framework.
   │
Monitoring/mgmt        NVML (NVIDIA Management Library — the API `nvidia-smi`
                        itself is built on) and DCGM (Data Center GPU Manager
                        — the production-grade fleet monitoring layer on top
                        of NVML, exporting to Prometheus).
   │
Framework              PyTorch / TensorFlow / JAX — call cuBLAS/cuDNN/NCCL
                       under the hood via a thin dispatch layer; almost none
                       of a framework's own code touches the GPU directly.
   │
Serving engine          vLLM / TensorRT-LLM / TGI (already covered in
                        tools-and-frameworks.md) — sit on top of the framework
                        layer, adding batching/scheduling logic.
```

**The single fact that resolves the most confusion**: a framework like PyTorch does not
"talk to the GPU" in any code it wrote itself for matrix multiplication — it calls into
cuBLAS. This is why a PyTorch version and a CUDA version are two separate compatibility
axes that both have to line up, and why "pip install torch" pulling a CUDA-bundled wheel
is solving exactly this pairing problem for you rather than being an implementation detail
that doesn't matter.

### Driver vs. Toolkit — the version rule that prevents the most common failure

The rule, stated precisely because getting the direction backwards is the actual mistake
people make: **the installed NVIDIA driver must support a CUDA version at least as new as
what the toolkit/application requires** — driver versions are backward-compatible with
older CUDA toolkit versions, not forward-compatible with newer ones. Concretely: a host
with an older driver cannot run a container built against a newer CUDA toolkit than that
driver supports, no matter what's inside the container — this is why GPU-enabled Docker
images pin a specific CUDA base image, and why a "CUDA driver version is insufficient"
error is a host-driver problem, not a container problem, even though it surfaces inside
the container.

```bash
nvidia-smi   # top-right corner shows "CUDA Version: 12.4" — this is the MAXIMUM
             # CUDA toolkit version this driver supports, not the toolkit installed
nvcc --version   # shows the actually-installed CUDA toolkit version, if any —
                 # a completely separate number, can legitimately be lower
```

### cuBLAS and cuDNN — the two libraries that do almost all the real work

- **cuBLAS** — dense linear algebra (matrix multiply, the BLAS standard's GPU
  implementation). Since a transformer's attention and MLP blocks are dominated by matrix
  multiplication, cuBLAS calls (specifically their Tensor-Core-accelerated variants) are
  where the vast majority of an LLM forward pass's GPU time is actually spent — this is
  the software-layer counterpart to
  [`03_gpu_architecture.md`'s Tensor Core explanation](03_gpu_architecture.md#cuda-cores-vs-tensor-cores-genuinely-different-hardware):
  cuBLAS is *how* a framework actually reaches the Tensor Cores, not a separate concern
  from them.
- **cuDNN** — neural-network-specific primitives: convolution, pooling, normalization,
  activation functions, attention kernels. Historically the CNN-era library; for
  transformers specifically, cuDNN's fused/optimized attention kernels (and increasingly,
  hand-written kernels like FlashAttention that bypass cuDNN's generic path for a
  faster, memory-aware implementation) are the relevant piece — worth naming that
  FlashAttention exists specifically because a generic cuDNN attention implementation
  wasn't memory-efficient enough for long-context transformers, a direct instance of the
  memory-bandwidth-first mental model from `03_gpu_architecture.md`.

### NVML and DCGM — the monitoring stack, precisely

- **NVML (NVIDIA Management Library)** — the actual C API for querying/controlling GPU
  state (utilization, memory, temperature, power, ECC errors). `nvidia-smi` is a thin CLI
  wrapper around NVML — anything `nvidia-smi` shows, NVML exposes programmatically.
- **DCGM (Data Center GPU Manager)** — built on top of NVML, adds fleet-scale features
  NVML alone doesn't: health checks, diagnostics, and critically, a **Prometheus
  exporter** (`dcgm-exporter`) that turns per-GPU NVML-level metrics into scraped,
  dashboarded time series. This is the exact tool named without explanation in
  [`aws-production-architecture.md`'s monitoring section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#monitoring-the-metrics-that-actually-matter-here)
  ("DCGM exporting to Prometheus is the standard source for the GPU side") — now with the
  actual mechanism behind that claim: DCGM is the fleet-management layer over NVML, not a
  competing or redundant tool.

## Deep-Dive: diagnosing a version-mismatch failure by layer

A concrete worked example, since this is the most common real GPU-infra incident shape:

1. **Symptom**: a container fails to initialize CUDA, or a framework reports "CUDA driver
   version is insufficient for CUDA runtime version."
2. **First check — driver layer**: `nvidia-smi` on the *host* (not inside the container).
   If this fails entirely, the driver/kernel module itself is broken — nothing above it
   can work regardless of container contents.
3. **Second check — the version pairing**: compare `nvidia-smi`'s reported max CUDA
   version against the CUDA version the container's base image was built against (check
   the image tag, e.g. `nvidia/cuda:12.4.0-runtime`). If the container's CUDA version
   exceeds the host driver's max supported version, this is the failure — and the fix is
   either a driver upgrade (a fleet-wide, host-level operation, not a per-container one)
   or pinning the container to an older CUDA base image.
4. **Third check — library-level, only if the above pass**: a working CUDA runtime but a
   framework-specific failure (e.g. PyTorch built against a different CUDA minor version
   than what's present) points to the framework/library layer instead — a `pip install`
   pairing problem, not a driver problem.

Naming which of these three layers is broken, in this order, is itself the diagnostic
skill — jumping straight to "reinstall everything" without isolating the layer is the
common, slow anti-pattern.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Pin an older CUDA toolkit version fleet-wide | Stability, fewer version-pairing incidents | Miss newer library optimizations (e.g. newer cuBLAS Tensor-Core kernel improvements) |
| Let each team choose its own CUDA/framework version | Flexibility per workload | Multiplies the version-pairing surface area the fleet has to support and diagnose |
| Use a hand-written kernel (FlashAttention) instead of cuDNN's generic path | Meaningfully faster, more memory-efficient for long context | Another dependency to version-pin and keep compatible with the CUDA/driver stack above |

## Failure Modes to Raise Proactively

- **Treating "CUDA" as one version number** — as shown above, driver version and toolkit
  version are two different numbers with a one-directional compatibility rule; conflating
  them is the single most common cause of "it works on my machine" GPU incidents.
- **Assuming a framework upgrade alone fixes a CUDA error** — if the underlying issue is
  the driver/toolkit pairing, no framework-level change fixes it; the fix has to happen at
  the correct layer, identified via the diagnostic sequence above.
- **Not distinguishing NVML-level metrics (what `nvidia-smi` shows) from DCGM's
  additional diagnostics** — a dashboard built directly on raw NVML polling duplicates
  what DCGM already provides, with less fleet-scale tooling around it (no built-in
  Prometheus exporter, no health-check framework) — reinventing a narrower version of an
  existing tool.

## Make It Yours

- Run `nvidia-smi` and `nvcc --version` (if installed) side by side on any machine with a
  GPU and confirm you can state, out loud, which number is the driver's ceiling and which
  is the actually-installed toolkit — the exact distinction that resolves the version
  mismatch failure mode above.
- Check whether `dcgm-exporter` is what's actually feeding any Grafana GPU dashboard
  you've built or seen in `platform-lab/mlops_aiops/` or `k8n_mlops/` — naming the real
  data-source chain (GPU → NVML → DCGM → Prometheus → Grafana) rather than treating
  "the dashboard" as the source of truth.

## Practice Questions

1. A container built against CUDA 12.4 fails to start on a host whose driver only
   supports up to CUDA 12.1 — which side needs to change, and why can't it be fixed by
   editing anything inside the container?
2. What does DCGM provide that raw NVML polling doesn't, and why does that matter at
   fleet scale specifically (not on a single dev machine)?
3. Why does a PyTorch model's forward pass spend most of its GPU time inside cuBLAS
   calls rather than in Python-level tensor code, and what does that imply about where
   performance tuning effort should go?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "CUDA isn't one thing — it's a stack: the driver (host-level,
kernel module), the toolkit (compiler/runtime, what you build against), math libraries
like cuBLAS and cuDNN that frameworks actually call for the heavy lifting, and a
monitoring layer (NVML, with DCGM built on top for fleet-scale metrics and Prometheus
export). Most 'CUDA errors' are actually version-pairing errors between these layers, and
diagnosing them means checking driver, then toolkit, then library — in that order."

**The follow-up-proof version**: be ready to explain *why* the driver/toolkit
compatibility is one-directional (backward-compatible, not forward-compatible) — the
driver ships the actual hardware-interfacing code, so a toolkit built for hardware
features or driver-side APIs a given driver predates simply cannot run, while an older
toolkit's simpler API surface is a subset any newer driver still supports.

**Vocabulary builder**: *userspace driver* (the driver component that runs as a normal
process, distinct from the `nvidia.ko` kernel module), *ABI compatibility* (why a
specific toolkit/driver pairing either works or doesn't, not "mostly works"), *exporter*
(a component like `dcgm-exporter` that translates a system's native metrics into
Prometheus's scrape format — the same pattern as any other Prometheus exporter, applied
to GPUs specifically).
