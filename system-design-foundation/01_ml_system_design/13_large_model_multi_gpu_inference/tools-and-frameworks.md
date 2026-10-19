# Tools Required: Multi-GPU, Multi-Node Inference Serving

Companion to [`tutorial.md`](tutorial.md) — that doc covers *why* a
~1TB model needs tensor + pipeline parallelism across multiple nodes;
this one covers *which real tools* actually implement that, what each
one is genuinely better at, and where the boundaries between them sit.
[`mlops_aiops/docs/tools/vllm/`](../../../../mlops_aiops/docs/tools/vllm/README.md)
is the hands-on, single-tool deep-dive on vLLM specifically (install,
run, PagedAttention/continuous-batching mechanics) — this doc is the
comparative layer above it.

## The layers, and which tool lives at which one

A production multi-node LLM deployment is not one tool — it's several,
stacked:

```
Orchestration / autoscaling     Ray Serve, KubeRay, SageMaker, EKS
        |
Inference serving engine        vLLM, TensorRT-LLM, TGI, SGLang, DeepSpeed-MII
        |
Parallelism runtime              Megatron-Core, DeepSpeed, or built into the engine above
        |
Collective communication         NCCL (GPU-to-GPU, all the above sit on top of it)
        |
Network fabric                    EFA (AWS), InfiniBand (on-prem/other clouds)
```

Getting confused about which layer a given tool operates at is the most
common source of "why can't I just use X for Y" questions — NCCL and
EFA are not choices you evaluate against vLLM; they're underneath it,
doing a different job.

## Inference serving engines — the actual choice most teams make

### vLLM

Already covered in depth in
[`mlops_aiops/docs/tools/vllm/`](../../../../mlops_aiops/docs/tools/vllm/README.md)
— PagedAttention for efficient KV cache management, continuous batching,
an OpenAI-compatible API. For **this tutorial's multi-node scenario**
specifically: vLLM supports tensor parallelism natively (`--tensor-
parallel-size`) and, via a **Ray backend**, pipeline parallelism and
multi-node deployment (`--pipeline-parallel-size` combined with a Ray
cluster spanning the nodes). It's the most common default choice today
precisely because it's open-source, actively developed, and the
OpenAI-compatible API means the rest of the stack (gateway, client
code) doesn't need to know it's talking to a self-hosted, sharded
model rather than a hosted API.

### TensorRT-LLM

NVIDIA's own inference engine, built on TensorRT and specifically
optimized for NVIDIA GPUs (which — for a ~1TB model — is almost
certainly what you're running on anyway). Supports tensor and pipeline
parallelism, in-flight (continuous) batching, and typically achieves
the **highest raw throughput per GPU** of the options here, at the cost
of a steeper setup process (models need to be compiled into
TensorRT-LLM's own engine format ahead of serving, rather than loaded
directly) and being NVIDIA-only. The trade a team is actually making
choosing this over vLLM: meaningfully better throughput/cost, for less
flexibility and a slower iteration loop when swapping models.

### Text Generation Inference (TGI)

Hugging Face's serving engine — tensor-parallel serving, tight
integration with the Hugging Face model ecosystem (loading a model by
its Hub ID directly), continuous batching. A reasonable default when a
team is already deep in the Hugging Face ecosystem for model management
and wants that same familiarity at serving time; less commonly the
top pick purely on throughput compared to vLLM or TensorRT-LLM today.

### SGLang

A newer engine built around **RadixAttention** — a prefix-caching
mechanism that shares KV cache across requests with a common prefix
(e.g. a shared system prompt, or branching generations in an agentic
workflow), which vLLM's PagedAttention doesn't do as aggressively by
default. Worth naming specifically for **agentic or structured-
generation workloads** — many parallel branches sharing a prefix is
exactly the pattern RadixAttention is built for — rather than as a
blanket vLLM replacement.

### DeepSpeed-Inference / DeepSpeed-MII

Microsoft's inference-side counterpart to the DeepSpeed training
library already named in [distributed training's Core
Concepts](../07_distributed_training_serving.md#ray-what-it-actually-provides).
Notably supports **ZeRO-Inference** — offloading part of the model to
CPU RAM or even NVMe when GPU memory genuinely can't fit it even after
the strategies above, trading latency for the ability to run at all on
a smaller GPU footprint. Worth knowing exists as the answer to "what if
I truly cannot get enough GPU memory" — a real, if slower, escape
valve most other engines here don't offer.

## Orchestration — the layer that actually spans nodes

Every engine above needs *something* to actually launch and coordinate
processes across multiple physical machines, handle a node dying
mid-request, and route traffic. This is a genuinely separate concern
from the serving engine itself:

- **Ray Serve / KubeRay** — a Ray cluster spans the nodes; vLLM and
  others use it as their multi-node backend directly (see vLLM above).
  Ray Serve additionally provides autoscaling and request routing on
  top, making it a natural single answer for "orchestrate the whole
  multi-node deployment," not just "run the parallelism runtime."
- **Amazon SageMaker — Large Model Inference (LMI) containers** — a
  managed option: pre-built containers wrapping DeepSpeed, TensorRT-LLM,
  or vLLM configurations, with SageMaker handling the underlying EC2
  fleet, networking, and endpoint management. The trade: less control
  over the exact serving stack, in exchange for not operating the
  orchestration layer at all — a real, legitimate choice for a team
  that wants to focus effort on the model/eval side, not the
  infrastructure side, discussed further in
  [`aws-production-architecture.md`](aws-production-architecture.md).
- **Amazon EKS (Kubernetes) with KubeRay** — the self-managed
  equivalent: full control over node groups, networking, and scaling
  policy, at the cost of operating that control plane. The natural
  choice once a team's needs (custom routing, multiple models, specific
  autoscaling logic) outgrow what SageMaker's managed layer exposes.

## Underneath everything: NCCL and EFA

**NCCL** (NVIDIA Collective Communications Library) is what every engine
above actually calls to move tensors between GPUs for tensor-parallel
and pipeline-parallel communication — it's not something a team
configures directly so much as something that has to be correctly
*available* (right driver/CUDA versions, correctly networked) for any
of the above to perform as expected. **EFA** (Elastic Fabric Adapter) is
AWS's answer to "NCCL needs a fast network between nodes" — instances
like `p5.48xlarge` expose EFA specifically so cross-node NCCL traffic
(pipeline-parallel activations, in this tutorial's architecture) doesn't
bottleneck on ordinary networking. Getting this wrong — deploying a
multi-node TP+PP setup on non-EFA instances — is a common, expensive
mistake: everything still *works*, just far slower, in a way that looks
like a software problem until someone checks the network layer.

## Quantization tooling

Referenced from [`tutorial.md`](tutorial.md#quantization-buying-back-memory-headroom-without-buying-more-gpus)
— the actual tools that produce a quantized model artifact:

- **AWQ (Activation-aware Weight Quantization)** and **GPTQ** — both
  produce int4/int8 quantized weights with calibration against a small
  representative dataset, widely supported as an input format across
  vLLM, TGI, and TensorRT-LLM.
- **FP8** — natively accelerated in H100/H200 hardware (not a software
  emulation of lower precision the way int4/int8 often are on older
  GPUs), making it frequently the best throughput-per-accuracy-loss
  trade-off on current-generation NVIDIA hardware specifically.
- **bitsandbytes** — a lighter-weight quantization path common in
  research/fine-tuning contexts; less commonly the production serving
  choice for a deployment at this scale compared to AWQ/GPTQ/FP8.

## Choosing among these, as an actual decision

| If the priority is... | Reach for |
|---|---|
| Fastest path to a working multi-node deployment, open ecosystem | vLLM + Ray |
| Maximum raw throughput per GPU, NVIDIA-only is acceptable | TensorRT-LLM |
| Heavy Hugging Face ecosystem integration already in place | TGI |
| Agentic/structured generation with heavy prefix sharing | SGLang |
| GPU memory genuinely insufficient even after TP+PP+quantization | DeepSpeed-Inference (ZeRO-Inference offload) |
| Minimize infrastructure operations, accept less stack control | SageMaker LMI |
| Full control over routing/scaling/multi-model serving | EKS + KubeRay |

None of these are permanent commitments — it's common and reasonable
for a team to prototype on vLLM (fastest iteration), then move a
stable, high-traffic model to TensorRT-LLM once the throughput
difference is worth the reduced flexibility. Naming that as a
deliberate two-stage plan, rather than picking one tool and treating it
as fixed forever, is itself a piece of staff-level signal.
