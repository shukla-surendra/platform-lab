#!/usr/bin/env python3
"""Human-facing CLI -- talks ONLY to coordinator_agent, never directly to weather_agent.

    python client.py "What's the weather in Tokyo?"
    python client.py "What is the capital of France?"
    python client.py                       # interactive REPL

This is the user's-eye view of the whole chain: you send one message to one agent
(coordinator_agent); whether it answers itself or silently calls weather_agent over
A2A on your behalf is invisible from here -- exactly the point of the protocol: a
client only ever needs to know how to talk to *one* agent's Agent Card, regardless
of how many other agents that agent delegates to internally.
"""

from __future__ import annotations

import asyncio
import sys

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageRequest

import config
from coordinator_agent.agent_executor import extract_response_text


async def ask(query: str) -> str:
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=config.COORDINATOR_AGENT_URL)
        agent_card = await resolver.get_agent_card()

        client = await create_client(agent=agent_card, client_config=ClientConfig(streaming=False))
        message = new_text_message(query, role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        chunks = [chunk async for chunk in client.send_message(request)]
        await client.close()

    return extract_response_text(chunks)


async def repl() -> None:
    print(f"Talking to coordinator_agent at {config.COORDINATOR_AGENT_URL}. Ctrl-D to exit.")
    while True:
        try:
            query = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not query:
            continue
        print(f"agent> {await ask(query)}")


def main() -> int:
    if len(sys.argv) > 1:
        print(asyncio.run(ask(" ".join(sys.argv[1:]))))
    else:
        asyncio.run(repl())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
