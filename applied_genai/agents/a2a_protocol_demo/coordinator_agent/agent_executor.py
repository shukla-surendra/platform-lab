"""The coordinator: the actual "agent talking to another agent" part of this demo.

It's an A2A *server* to the human (or client.py) talking to it -- and, inside its own
`execute`, an A2A *client* to weather_agent, a completely separate running process it
discovers via that agent's own published Agent Card and calls over real HTTP/JSON-RPC.
Not a Python import, not a function call -- a genuine network request to another agent,
which is the whole point A2A exists to standardize (see ../README.md).
"""

from __future__ import annotations

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_message_text, new_task_from_user_message, new_text_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Role, SendMessageRequest, TaskState
from langchain_ollama import ChatOllama

import config

CLASSIFY_PROMPT = (
    "You are a routing classifier, not a conversationalist. Decide whether this "
    "request needs a WEATHER specialist agent, or whether you should answer it "
    "yourself directly. Reply with exactly one word: WEATHER or DIRECT.\n\n"
    "Request: {query}"
)


def extract_response_text(chunks: list) -> str:
    """Best-effort text extraction from client.send_message()'s streamed chunks.

    NOTE: this is the one part of this project not directly run against a live
    a2a-sdk install while writing it -- the official sample only ever does
    `print(chunk)`, not shown attribute access. If this doesn't extract cleanly
    against your installed SDK version, add `print(repr(chunk))` in the loop
    below and adjust the attribute path to match what actually comes back --
    the shape is a Task or Message object with nested Parts either way.
    """
    texts = []
    for chunk in chunks:
        artifacts = getattr(chunk, "artifacts", None) or []
        for artifact in artifacts:
            for part in getattr(artifact, "parts", []) or []:
                text = getattr(part, "text", None)
                if text:
                    texts.append(text)
        parts = getattr(chunk, "parts", None) or []
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                texts.append(text)
    return texts[-1] if texts else str(chunks[-1]) if chunks else "(no response from weather_agent)"


class CoordinatorAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.llm = ChatOllama(model=config.OLLAMA_MODEL, base_url=config.OLLAMA_BASE_URL, temperature=0)

    async def _ask_weather_agent(self, query: str) -> str:
        """The actual agent-to-agent call: discover weather_agent's Agent Card,
        then send it a real A2A message. Everything above this method is the
        coordinator's own local reasoning; this is the moment it leaves its own
        process and talks to another agent as a protocol client."""
        async with httpx.AsyncClient() as httpx_client:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=config.WEATHER_AGENT_URL)
            weather_agent_card = await resolver.get_agent_card()

            client = await create_client(
                agent=weather_agent_card,
                client_config=ClientConfig(streaming=False),
            )
            message = new_text_message(query, role=Role.ROLE_USER)
            request = SendMessageRequest(message=message)

            chunks = [chunk async for chunk in client.send_message(request)]
            await client.close()

        return extract_response_text(chunks)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        await updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message("Thinking..."),
        )

        query = get_message_text(context.message) or ""

        decision = self.llm.invoke(CLASSIFY_PROMPT.format(query=query)).content.strip().upper()

        if "WEATHER" in decision:
            await updater.update_status(
                state=TaskState.TASK_STATE_WORKING,
                message=new_text_message("Delegating to weather_agent over A2A..."),
            )
            delegated = await self._ask_weather_agent(query)
            result = f"[delegated to weather_agent] {delegated}"
        else:
            response = self.llm.invoke(query)
            result = response.content

        await updater.add_artifact(parts=[new_text_part(text=result, media_type="text/plain")])
        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message("Done."),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel is not supported.")
