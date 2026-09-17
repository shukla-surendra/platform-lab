"""The weather agent's A2A server -- run standalone, on its own port.

    python -m weather_agent

Publishes an Agent Card describing exactly one skill ("weather_lookup"), so any A2A
client (including coordinator_agent/, in this project) can discover what this agent
can do before ever sending it a message.
"""

from __future__ import annotations

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from starlette.applications import Starlette

import config
from weather_agent.agent_executor import WeatherAgentExecutor

if __name__ == "__main__":
    skill = AgentSkill(
        id="weather_lookup",
        name="Weather Lookup",
        description="Reports current weather for a small set of known cities.",
        input_modes=["text/plain"],
        output_modes=["text/plain"],
        tags=["a2a-protocol-demo", "weather"],
        examples=["What's the weather in Paris?", "Tokyo weather"],
    )

    agent_card = AgentCard(
        name="Weather Agent",
        description="Reports current weather for a small set of known cities.",
        version="0.1.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                url=config.WEATHER_AGENT_URL,
                protocol_version="1.0",
            )
        ],
        skills=[skill],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=WeatherAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, "/"))

    app = Starlette(routes=routes)

    print(f"weather_agent serving at {config.WEATHER_AGENT_URL}")
    uvicorn.run(app, host=config.WEATHER_AGENT_HOST, port=config.WEATHER_AGENT_PORT)
