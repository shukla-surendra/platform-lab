#!/usr/bin/env python3
"""Concurrent load test against the vLLM server — makes vLLM's continuous
batching visible instead of theoretical.

Run it once with --concurrency 1, then again with --concurrency 16 against
the SAME server and compare aggregate tokens/sec: single-request latency
barely changes, but total throughput climbs a lot faster than 16x slower
per-request would suggest — that gap IS continuous batching (vLLM packs
many in-flight sequences onto the GPU together instead of one at a time).
Past some concurrency level throughput flattens as the GPU/KV-cache
saturates — that ceiling is exactly what --gpu-memory-utilization and
--max-model-len (see the GPU/LLM guide) control.

Usage:
    python benchmark.py --host <public_ip> --concurrency 8 --requests 40
"""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

PROMPTS = [
    "Explain the difference between latency and throughput in one paragraph.",
    "Write a short poem about GPUs.",
    "List three benefits of continuous batching in LLM serving.",
    "Summarize what PagedAttention does, in two sentences.",
]


def one_request(client: OpenAI, model: str, prompt: str, max_tokens: int) -> tuple[float, int]:
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    elapsed = time.perf_counter() - start
    return elapsed, response.usage.completion_tokens


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--requests", type=int, default=40, help="Total requests to send")
    parser.add_argument("--concurrency", type=int, default=8, help="Requests in flight at once")
    parser.add_argument("--max-tokens", type=int, default=128)
    args = parser.parse_args()

    client = OpenAI(base_url=f"http://{args.host}:{args.port}/v1", api_key=args.api_key or "not-needed")

    print(f"Sending {args.requests} requests at concurrency {args.concurrency}...")
    wall_start = time.perf_counter()
    latencies: list[float] = []
    token_counts: list[int] = []

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(one_request, client, args.model, PROMPTS[i % len(PROMPTS)], args.max_tokens)
            for i in range(args.requests)
        ]
        for future in as_completed(futures):
            elapsed, completion_tokens = future.result()
            latencies.append(elapsed)
            token_counts.append(completion_tokens)

    wall_elapsed = time.perf_counter() - wall_start
    total_tokens = sum(token_counts)
    latencies.sort()

    def pct(p: float) -> float:
        idx = min(int(len(latencies) * p), len(latencies) - 1)
        return latencies[idx]

    print()
    print(f"Wall time:            {wall_elapsed:.2f}s")
    print(f"Requests completed:   {len(latencies)}")
    print(f"Total tokens:         {total_tokens}")
    print(f"Aggregate throughput: {total_tokens / wall_elapsed:.1f} tokens/sec")
    print(f"Per-request latency — p50: {pct(0.50):.2f}s  p95: {pct(0.95):.2f}s  p99: {pct(0.99):.2f}s")
    print(f"Mean latency:         {statistics.mean(latencies):.2f}s")


if __name__ == "__main__":
    main()
