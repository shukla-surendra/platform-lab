"""The coordinator agent's A2A server -- run standalone, on its own port.

    python -m coordinator_agent

Answers general questions itself (via a local Ollama LLM), but delegates anything
weather-related to weather_agent/ over a real A2A call -- see agent_executor.py for
the actual delegation logic. Start weather_agent first; this one depends on it being
reachable.
"""

from __future__ import annotations

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from starlette.applications import Starlette

import config
from coordinator_agent.agent_executor import CoordinatorAgentExecutor

if __name__ == "__main__":
    skill = AgentSkill(
        id="general_qa_with_weather_delegation",
        name="General Q&A (delegates weather questions)",
        description=(
            "Answers general questions directly using a local LLM. Recognizes "
            "weather-related requests and delegates them to a separate Weather "
            "Agent over the A2A protocol instead of answering them itself."
        ),
        input_modes=["text/plain"],
        output_modes=["text/plain"],
        tags=["a2a-protocol-demo", "coordinator"],
        examples=["What's the weather in Paris?", "What is the capital of France?"],
    )

    agent_card = AgentCard(
        name="Coordinator Agent",
        description="Answers directly, or delegates weather questions to Weather Agent.",
        version="0.1.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                url=config.COORDINATOR_AGENT_URL,
                protocol_version="1.0",
            )
        ],
        skills=[skill],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=CoordinatorAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, "/"))

    app = Starlette(routes=routes)

    print(f"coordinator_agent serving at {config.COORDINATOR_AGENT_URL}")
    print(f"  -> will delegate weather questions to {config.WEATHER_AGENT_URL}")
    uvicorn.run(app, host=config.COORDINATOR_AGENT_HOST, port=config.COORDINATOR_AGENT_PORT)
