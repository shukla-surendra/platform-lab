#!/usr/bin/env python3
"""Runs through every primitive this from-scratch implementation supports, against the
from-scratch server, printing the full wire trace as it goes: initialize handshake, tools/list,
tools/call (including an argument-validation error and an unknown-tool error), resources/list,
resources/read.

Usage:
  python demo.py            # full trace to stderr, human-readable results to stdout
  python demo.py --quiet    # suppress the wire trace, just show results
"""

from __future__ import annotations

import sys

from genai_lab.rag.mcp_from_scratch.mcp_client import MCPClient, MCPError


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    verbose = "--quiet" not in sys.argv

    with MCPClient([sys.executable, "mcp_server.py"], verbose=verbose) as client:
        section("1. initialize handshake")
        info = client.initialize()
        print(f"server: {info['serverInfo']['name']} v{info['serverInfo']['version']}, "
              f"protocol {info['protocolVersion']}, capabilities {list(info['capabilities'])}")

        section("2. tools/list")
        for tool in client.list_tools():
            print(f"- {tool['name']}: {tool['description']}")

        section("3. tools/call -- happy path")
        print(client.call_tool("mcp_add_task", {"title": "understand MCP from scratch"}))
        print(client.call_tool("mcp_add_task", {"title": "compare against tasks_mcp_server.py"}))
        print(client.call_tool("mcp_list_tasks"))
        print(client.call_tool("mcp_complete_task", {"task_id": 1}))
        print(client.call_tool("mcp_list_tasks"))

        section("4. tools/call -- protocol-level error (unknown tool)")
        try:
            client.call_tool("mcp_delete_everything", {})
        except MCPError as exc:
            print(f"caught MCPError as expected: {exc}")

        section("5. tools/call -- protocol-level error (missing required argument)")
        try:
            client.call_tool("mcp_add_task", {})
        except MCPError as exc:
            print(f"caught MCPError as expected: {exc}")

        section("6. resources/list and resources/read")
        for resource in client.list_resources():
            print(f"- {resource['uri']}: {resource['description']}")
        print(client.read_resource("tasks://all"))

    section("done")
    print("client closed stdin; server saw EOF and exited cleanly (see trace above)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
