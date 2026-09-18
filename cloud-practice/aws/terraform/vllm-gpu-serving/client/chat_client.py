#!/usr/bin/env python3
"""Talk to the vLLM OpenAI-compatible server started by this module.

vLLM implements the OpenAI Chat Completions API, so the official `openai`
SDK works unmodified — just point base_url at the instance and swap the
model name. Two things are worth noticing while you read this file:

  1. The SDK requires a NON-EMPTY api_key even when the server was started
     without --api-key (i.e. doesn't check it at all) — "not-needed" below
     is a placeholder to satisfy the client library, not a real credential.
  2. Streaming (--stream) is the same request, just a different iteration
     pattern — see chat_streaming() below. This is what a real chat UI uses
     so the first token appears immediately instead of after the whole
     response is generated.

Usage:
    python chat_client.py --host <public_ip> --prompt "Explain vLLM in one sentence."
    python chat_client.py --host <public_ip> --stream --prompt "Write a haiku about GPUs."
"""

import argparse

from openai import OpenAI


def build_client(host: str, port: int, api_key: str) -> OpenAI:
    return OpenAI(base_url=f"http://{host}:{port}/v1", api_key=api_key or "not-needed")


def chat_once(client: OpenAI, model: str, prompt: str) -> None:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        temperature=0.7,
    )
    choice = response.choices[0]
    print(choice.message.content)
    print(
        f"\n--- usage: prompt={response.usage.prompt_tokens} "
        f"completion={response.usage.completion_tokens} "
        f"total={response.usage.total_tokens} tokens ---"
    )


def chat_streaming(client: OpenAI, model: str, prompt: str) -> None:
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        temperature=0.7,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()


def list_models(client: OpenAI) -> None:
    for model in client.models.list().data:
        print(model.id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Instance public IP or DNS name")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--api-key", default="", help="Only needed if the server was started with --api-key")
    parser.add_argument("--prompt", default="Say hello in five words.")
    parser.add_argument("--stream", action="store_true", help="Stream tokens as they're generated")
    parser.add_argument("--list-models", action="store_true", help="Just list what the server reports and exit")
    args = parser.parse_args()

    client = build_client(args.host, args.port, args.api_key)

    if args.list_models:
        list_models(client)
        return

    if args.stream:
        chat_streaming(client, args.model, args.prompt)
    else:
        chat_once(client, args.model, args.prompt)


if __name__ == "__main__":
    main()
