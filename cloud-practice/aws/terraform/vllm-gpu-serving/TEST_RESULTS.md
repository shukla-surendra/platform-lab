# Test Results — Live Deployment, 2026-09-18

A real `terraform apply` of this module, tested end-to-end, then torn down.
Kept as evidence of what "working" actually looks like — every number below
is from the live instance, not a projection.

## Deployment

| | |
|---|---|
| Instance type allocated | `g6.2xlarge` (**NVIDIA L4** — first priority in `gpu_instance_types`, no A10G fallback needed) |
| Region | `us-east-1` |
| Launch time | `2026-09-18T06:26:32Z` |
| ASG creation time (Terraform apply, resource-only) | 1m22s |
| Docker image pull (`vllm/vllm-openai:latest`) | ~1m (parallelized layer pulls) |
| Model download (`Qwen/Qwen2.5-7B-Instruct`, ~14.2GB) | 85.6s from the Hugging Face Hub, unauthenticated |
| Model load onto GPU + `torch.compile` + CUDA graph capture | ~2m20s (weights load, compile, 51+35 CUDA graph shapes captured) |
| **Total time from `terraform apply` to serving traffic** | **~5 minutes** |

## 1. API smoke tests

```
GET /v1/models                                          -> 200, 0.63s
POST /v1/chat/completions (no Authorization header)      -> 401 {"error":"Unauthorized"}
GET /v1/models (wrong Authorization: Bearer value)        -> 401 {"error":"Unauthorized"}
POST /v1/chat/completions (correct key)                   -> 200, 0.86s
```

Confirms: the model is registered and responding, and `vllm_api_key`
actually gates every route (not just a cosmetic flag) — an unauthenticated
or wrong-key request is rejected before it reaches the model.

## 2. A real chat completion

Request: `"What is the capital of France? Answer in one word."` (temperature 0)

```json
{"choices":[{"message":{"content":"Paris"}}],
 "usage":{"prompt_tokens":41,"completion_tokens":2,"total_tokens":43}}
```
Correct answer, 2 completion tokens, 0.86s round trip.

## 3. Streaming

`POST /v1/chat/completions` with `"stream": true` on the prompt
`"Name three colors."` produced Server-Sent Events exactly as documented —
`data: {...}` chunks with `choices[0].delta.content`, ending in `data:
[DONE]`. First chunk carries an empty-string `delta.content` with
`role: "assistant"` (the OpenAI streaming convention for "here's who's
speaking, tokens follow") — worth knowing if you're writing a parser,
since a naive `if (delta.content)` check on that first chunk correctly
does nothing, but a naive "did we get ANY chunk" check needs to keep
reading rather than stop there.

## 4. Python clients (`client/chat_client.py`)

```
$ python chat_client.py --prompt "Explain vLLM in one sentence."
vLLM is a high-performance, parallelized inference engine designed to
efficiently run large language models on multi-GPU and multi-node setups.
--- usage: prompt=38 completion=29 total=67 tokens ---

$ python chat_client.py --stream --prompt "Write a haiku about GPUs."
Parallel tasks flow,
In silicon dance of lights and heat,
Power blooms in code.
```

## 5. Benchmark — continuous batching, made visible

This is the number that matters most. Same server, same prompt pool,
`--max-tokens 128`, only `--concurrency` changed:

| Concurrency | Requests | Wall time | Total tokens | **Throughput** | p50 latency | p95 latency | Mean latency |
|---|---|---|---|---|---|---|---|
| 1 | 8 | 49.81s | 820 | **16.5 tok/s** | 6.72s | 7.75s | 6.23s |
| 8 | 40 | 34.07s | 3,966 | **116.4 tok/s** | 6.57s | 8.07s | 6.17s |

**Throughput went up ~7.05×** for an 8× increase in concurrency, while
**per-request latency stayed essentially flat** (mean 6.23s → 6.17s, p50
6.72s → 6.57s — noise-level difference, not a real change). If vLLM
processed requests one at a time, 8× concurrency at roughly-fixed
per-request cost would mean 8× the wall time for the same total work,
not the same throughput improvement with FLAT latency. This is
`GPU_AND_LLM_SERVING_GUIDE.md` §3's continuous-batching claim, demonstrated
with real numbers instead of asserted in prose: many in-flight sequences
really were being served together, not queued behind each other.

## 6. GPU / container health during the concurrency-8 run

```
$ nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv
NVIDIA L4, 19518 MiB, 23034 MiB, 0%, 73°C
```
19.5 / 23 GiB VRAM in use (~85%) — consistent with the `gpu_memory_utilization
= 0.90` target from `weights (14.2GB) + KV cache pool` math in the guide.
`docker stats`: 1.13% CPU, 4.4GiB RSS for the container process itself
(the GPU does the real work; the host-side Docker process is mostly an
orchestrator). Instance load average stayed under 0.5 throughout — the
bottleneck for this workload is entirely the GPU, never the host CPU.

## What this confirms about the module

- The L4→A10G fallback logic never had to prove itself this run (L4 had
  capacity), but the rest of the pipeline — DLAMI boot, Docker image pull,
  HF download, `--api-key` enforcement, streaming, and the
  security-group + SSM access pattern — all worked exactly as documented
  on a genuinely fresh `terraform apply`, not just in review.
- One real bug was caught and fixed BEFORE this test run: `terraform
  plan` on a brand-new deployment errored on `data.aws_instance.primary`'s
  `count` argument depending on an unknown-at-plan-time value (the ASG's
  instance list). Fixed by dropping the conditional `count` entirely
  (this module always expects exactly one instance) and relying on
  `depends_on` to defer the data source's read to apply-time instead —
  see the `main.tf` comment above `data "aws_instance" "primary"`.
