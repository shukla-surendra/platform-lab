"""Builds the `MultiServerMCPClient` that connects to both MCP servers and exposes their tools
as LangChain-compatible tools the LangGraph agent can bind and call.

Two transports, selected by `config.MCP_TRANSPORT`:

- **stdio** (default, local dev): spawns both servers as subprocesses. This is the one place
  `APPLY_CHANGES` crosses the process boundary for that mode -- passed into the ops server's
  environment here, at spawn time, per invocation (see `mcp_servers/ops_server.py`'s docstring).
- **http** (docker-compose / production simulation): connects to already-running network
  services by URL. Nothing is spawned, and `apply_changes` here is *advisory only* -- the real
  gate is whatever `APPLY_CHANGES` the ops-server container was started with. A client can't grant
  itself write access to a shared service by passing a flag; that's the point.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

import config


def build_client(apply_changes: bool = False) -> MultiServerMCPClient:
    if config.MCP_TRANSPORT == "http":
        if apply_changes:
            print(
                "WARNING: --apply has no effect with MCP_TRANSPORT=http -- the dry-run gate is "
                "fixed by the running ops-server container's own APPLY_CHANGES env var, not by "
                "this client. Restart that container with APPLY_CHANGES=true to actually mutate "
                "state.",
                file=sys.stderr,
            )
        return MultiServerMCPClient(
            {
                "ops": {"transport": "streamable_http", "url": config.OPS_SERVER_URL},
                "knowledge": {"transport": "streamable_http", "url": config.KNOWLEDGE_SERVER_URL},
            }
        )

    ops_env = {**os.environ, "APPLY_CHANGES": "true" if apply_changes else "false"}
    return MultiServerMCPClient(
        {
            "ops": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [config.OPS_SERVER_SCRIPT],
                "env": ops_env,
            },
            "knowledge": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [config.KNOWLEDGE_SERVER_SCRIPT],
                "env": dict(os.environ),
            },
        }
    )


async def load_tools(apply_changes: bool = False) -> dict[str, list]:
    """Return {"ops": [...], "knowledge": [...]} -- tools split by server so graph.py can bind
    the right subset per node (e.g. gather_context only needs `ops`, retrieve_knowledge only
    needs `knowledge`) instead of exposing every tool to every LLM call."""
    client = build_client(apply_changes)
    ops_tools = await client.get_tools(server_name="ops")
    knowledge_tools = await client.get_tools(server_name="knowledge")
    return {"ops": ops_tools, "knowledge": knowledge_tools}


def _parse_result(result: Any) -> Any:
    """MCP tool results arrive as a list of content blocks (`[{"type": "text", "text": ...}]`).
    Tools here return either a JSON-serialized dict/list (parse it back) or a plain string
    (log tails, DRY RUN messages) -- fall back to the raw text when it isn't valid JSON."""
    if isinstance(result, list):
        text = "".join(block.get("text", "") for block in result if isinstance(block, dict))
    else:
        text = str(result)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


async def call_tool(tools_by_name: dict[str, Any], name: str, **kwargs: Any) -> Any:
    """Invoke one MCP tool by name against a {name: tool} dict (as built from `load_tools`'s
    lists) and return its parsed result. Each call opens a fresh stdio session under the hood --
    see langchain-mcp-adapters' `get_tools` docstring -- so this is not cheap in a tight loop,
    but it's the correct, stateless way this adapter is designed to be used."""
    return _parse_result(await tools_by_name[name].ainvoke(kwargs))
