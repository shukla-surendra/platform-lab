# Running a ~1TB LLM in Production: Multi-GPU, Multi-Node Inference

Three docs, meant to be read in order:

1. **[`tutorial.md`](tutorial.md)** — the core mental model. Why a ~1TB
   model is a memory problem before it's a compute problem, why that
   forces *multi-node* (not just multi-GPU) serving, tensor vs.
   pipeline parallelism and which bandwidth tier each belongs on, the
   KV-cache memory math nobody budgets for upfront, and a worked
   cluster-sizing example. Ends with the standard
   Trade-offs/Failure-Modes/Practice-Questions/Articulate-It sections
   this book's tutorials all use.
2. **[`tools-and-frameworks.md`](tools-and-frameworks.md)** — the real
   tools that implement the mental model above: vLLM, TensorRT-LLM,
   TGI, SGLang, DeepSpeed-Inference as serving engines; Ray Serve/
   KubeRay/SageMaker as orchestration; NCCL/EFA as the communication
   layer underneath all of it; AWQ/GPTQ/FP8 for quantization. Includes
   a decision table for picking among them.
3. **[`aws-production-architecture.md`](aws-production-architecture.md)**
   — the concrete AWS solution: which GPU instances, EFA networking and
   placement groups, FSx-backed weight loading, SageMaker LMI vs.
   self-managed EKS+KubeRay — and, the part most system-design answers
   skip, how it's actually *operated*: the metrics that matter for this
   specific workload, why autoscaling has to move by whole node-groups,
   why a rolling update is a real cost decision at this scale, and cost
   management day to day.

## How this relates to the rest of this book

Builds on [Distributed Training & Ray/Ray Serve](../07_distributed_training_serving.md)
(parallelism strategies, there framed for training) and
[LLMOps](../11_llmops.md) (the eval-gate/guardrail discipline this
folder's rollout section reuses directly). Sits alongside
[Model Serving & Deployment](../04_model_serving_deployment.md) and its
[DeepSeek-OCR-2 AWS hosting deep-dive](../04_model_serving_deployment_deepseek_ocr_aws_hosting.md)
— that deep-dive is the same *kind* of exercise (real model, real AWS
deployment-option elimination) at a much smaller scale (a 6.8GB model);
this folder is what changes once the model itself no longer fits on one
machine. [`mlops_aiops/docs/tools/vllm/`](../../../../mlops_aiops/docs/tools/vllm/README.md)
is the hands-on, single-tool version of the serving-engine layer this
folder's `tools-and-frameworks.md` compares against its alternatives.
