#!/usr/bin/env python3
"""AgentCore runtime entrypoint for the LangGraph demo."""

from __future__ import annotations

from bedrock_agentcore import BedrockAgentCoreApp

from langgraph_agents_demo import run_demo

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(request):
    prompt = request.get("prompt", "What is LangGraph and what is 17 * 9?")
    return {"result": run_demo(prompt)}


if __name__ == "__main__":
    app.run()
