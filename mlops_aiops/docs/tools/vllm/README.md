# vLLM

**Category:** LLM inference / serving

## What it is

Open-source, high-throughput and memory-efficient inference and serving
engine for large language models, from UC Berkeley's Sky Computing Lab.
It exposes an **OpenAI-compatible HTTP API** (`vllm serve <model>`), so
anything already written against the OpenAI SDK/client libraries can point
at a self-hosted model instead of a hosted API with no code changes.

Two ideas make it a production-serving engine rather than a single-user
tool:

- **PagedAttention** — manages the KV cache (the per-token attention state
  that grows as a model generates tokens) using paging techniques borrowed
  from OS virtual memory. This avoids the memory fragmentation that a
  naive fixed-allocation KV cache suffers from, and lets far more
  concurrent requests fit in the same GPU memory.
- **Continuous batching** — requests join and leave an in-flight batch
  dynamically as they arrive/finish, instead of waiting for a fixed-size
  batch to fill before starting. This keeps GPU utilization high under
  real, uneven request traffic, rather than the throughput cliff a naive
  static-batch server hits.

It also supports tensor/pipeline parallelism (splitting one large model
across multiple GPUs) and several quantization formats (AWQ, GPTQ, FP8) to
fit bigger models per GPU.

## What it's used for

Self-hosting open-weight LLMs (Llama, Mistral, Qwen, Mixtral, DeepSeek,
etc.) at production-grade throughput — the answer to "I want to run my own
model" once the requirement moves past a single developer's laptop to
serving real concurrent traffic. Typical reasons to reach for this instead
of always calling a hosted API: cost control at volume, data residency/
compliance, or serving a fine-tuned model that doesn't exist as a hosted
API at all.

## Where this fits against what's already in this repo

- **`genai_lab/langgraph_ollama_agent`, `bedrock_agentcore_demo`, and
  `databricks_autopilot_agent`** all use **Ollama** for their local model.
  Ollama is a friendly wrapper around **llama.cpp**, built for one
  developer running one quantized (GGUF) model locally — it was never
  designed for concurrent multi-user throughput. vLLM is the
  production-scale answer to the same underlying question ("run an
  open-weight model myself") once you need to serve more than one session
  at a time. Swapping one of these agents from Ollama to vLLM is mostly a
  base-URL change, since both speak an OpenAI-compatible-ish API surface
  (Ollama's own API, or its OpenAI-compatible endpoint) — the agent/graph
  code itself doesn't need to change.
- **`k8n_explorer/kserve-inference`** already demos KServe's
  `InferenceService` pattern for a plain sklearn model
  (`modelFormat: sklearn`). That exact same Helm chart pattern generalizes
  directly to LLM serving: KServe ships a built-in Hugging Face
  `ServingRuntime` that can run **vLLM as its backend**, so the same
  `InferenceService` abstraction (autoscaling, scale-to-zero, a
  storage-backed model artifact) applies to an LLM deployment with a
  different `modelFormat`/`runtime`, not a different platform.

## Related / competing engines

| Tool | Angle |
|---|---|
| **Hugging Face TGI** (Text Generation Inference) | Same goal as vLLM — HF-maintained, Rust-based server, also does continuous batching |
| **NVIDIA TensorRT-LLM** | Deepest hardware-specific optimization on NVIDIA GPUs — typically the highest raw throughput, but more complex (needs a model-specific compiled engine); usually fronted by **NVIDIA Triton Inference Server** as the actual serving layer |
| **llama.cpp** | CPU/consumer-GPU, quantized (GGUF) inference — the engine Ollama wraps |
| **Ollama** | A friendly local wrapper around llama.cpp — single-user dev convenience, not a production throughput engine; already used in this repo (see above) |
| **SGLang** | Similarly high-performance, adds structured/constrained generation as a first-class feature, same research lineage as vLLM |
| **MLC-LLM / LMDeploy** | More edge/mobile-oriented, or China-ecosystem-oriented, alternatives |

For a Kubernetes/EKS deployment specifically, vLLM (or TensorRT-LLM via
Triton) sits behind KServe or a plain Deployment+Service the same way any
other model-serving container would — see
[`docs/observability-on-eks.md`](../../observability-on-eks.md) for how
metrics/logs from that serving pod would get monitored once it's running.

## Multi-node: where Ray comes in

Single GPU, or tensor-parallel across multiple GPUs on **one** node, needs no
Ray at all — vLLM's own multiprocessing backend (`distributed_executor_backend:
"mp"`, the default) handles that locally over NCCL. The moment a deployment
spans **multiple nodes** — the model doesn't fit on one machine's GPUs, or
you're running many replicas that need a shared scheduler — vLLM switches
that same setting to `"ray"` and delegates cross-node process placement to
[Ray](../ray/README.md), the same way it delegates KV-cache management to
PagedAttention instead of reinventing it. If that Ray cluster itself runs on
Kubernetes, [KubeRay](../kuberay/README.md) is the operator managing it as a
`RayCluster` resource. Full layering (vLLM → Ray → KubeRay → Kubernetes), with
diagrams, in [`kuberay/conversation.md`](../kuberay/conversation.md).
