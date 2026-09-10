#!/usr/bin/env python3
"""A from-scratch MCP server: no `mcp` package, just jsonrpc.py + stdio_transport.py + the
dispatch loop below. It speaks the same tools (mcp_list_tasks, mcp_add_task, mcp_complete_task)
as ../bedrock_agentcore_demo/tasks_mcp_server.py, so you can compare this file to that one directly to see exactly what
the real SDK (FastMCP) is doing for you: JSON Schema generation from type hints, transport
abstraction (stdio here, but also Streamable HTTP), and error-handling boilerplate.

This process is meant to be launched as a subprocess by mcp_client.py (or by any MCP client, like
Claude Desktop, pointed at `python mcp_server.py`) -- it is never run interactively. Its stdin/
stdout are the wire; see stdio_transport.py's docstring for why nothing but JSON-RPC messages may
ever touch stdout.

Run it directly for a syntax/import sanity check only:
    python mcp_server.py < /dev/null
(it will read EOF from /dev/null immediately and exit -- see main() below.)

Background mode (`--pipe-in`/`--pipe-out`): the two arguments name a pair of named pipes (FIFOs,
see `make server-bg`) to use instead of stdin/stdout. dispatch() and the read/write loop below
don't change at all -- they already operate on generic streams, so a FIFO pair is just as valid a
transport as a subprocess's piped stdin/stdout. This is what makes it possible to start the server
once, in the background, and have a separate process (e.g. a Jupyter kernel) attach to it later
instead of spawning a fresh server per client, which is all mcp_client.py's MCPClient(...) does.
"""

from __future__ import annotations

import sys
from typing import Any, TextIO

import genai_lab.rag.mcp_from_scratch.jsonrpc as jsonrpc
import genai_lab.rag.mcp_from_scratch.task_store as task_store
from genai_lab.rag.mcp_from_scratch.stdio_transport import read_message, trace, write_message

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "mcp-from-scratch-tasks", "version": "0.1.0"}

# --- tool definitions ---------------------------------------------------------------------------
#
# In the real SDK (FastMCP, used by ../bedrock_agentcore_demo/tasks_mcp_server.py), this JSON Schema is generated for you
# from a function's type hints and docstring. Here we write it by hand, which is exactly why it's
# worth writing by hand once: it makes concrete what "inputSchema" actually is -- plain JSON
# Schema, the same format used by REST API specs and form validators, nothing MCP-specific.

TOOLS: list[dict[str, Any]] = [
    {
        "name": "mcp_list_tasks",
        "description": "Return all tasks and their completion state.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "mcp_add_task",
        "description": "Add a new task by title.",
        "inputSchema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
    },
    {
        "name": "mcp_complete_task",
        "description": "Mark a task as complete by id.",
        "inputSchema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
]

RESOURCES: list[dict[str, Any]] = [
    {
        "uri": "tasks://all",
        "name": "All tasks",
        "description": "The full current task list as plain text.",
        "mimeType": "text/plain",
    }
]


def _validate_args(schema: dict[str, Any], arguments: dict[str, Any]) -> str | None:
    """Minimal hand-rolled validation -- just required-field presence and a basic type check.
    The real spec expects full JSON Schema validation (a proper `jsonschema` library call); this
    is the simplified version, enough to demonstrate why validation happens at all: a model can
    and will occasionally send a tool call with a missing or wrong-typed argument.
    """
    type_map = {"string": str, "integer": int}
    for field in schema.get("required", []):
        if field not in arguments:
            return f"missing required argument '{field}'"
    for field, value in arguments.items():
        expected = schema.get("properties", {}).get(field, {}).get("type")
        py_type = type_map.get(expected)
        if py_type is not None and not isinstance(value, py_type):
            return f"argument '{field}' must be of type {expected}, got {type(value).__name__}"
    return None


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool and return an MCP tool-call result.

    Important distinction the MCP spec draws, easy to get wrong: a tool that *runs* but fails
    (bad task id, business-logic error) is still a JSON-RPC *success* response, with
    `isError: true` inside the result -- so the model sees the failure as a normal message and can
    react to it. Only protocol-level problems (unknown method, malformed request) are JSON-RPC
    errors. That's why _call_tool never raises for "task not found" but does for an unknown tool
    name below, in dispatch(), as an INVALID_PARAMS protocol error.
    """
    if name == "mcp_list_tasks":
        text = task_store.list_tasks()
    elif name == "mcp_add_task":
        text = task_store.add_task(str(arguments["title"]))
    elif name == "mcp_complete_task":
        text = task_store.complete_task(int(arguments["task_id"]))
    else:
        raise KeyError(name)  # caller (dispatch) already validated this can't happen

    return {"content": [{"type": "text", "text": text}], "isError": False}


def dispatch(message: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one incoming request/notification, return a response dict or None (for
    notifications, which get no reply at all).
    """
    method = message.get("method")
    params = message.get("params", {}) or {}
    id_ = message.get("id")  # present for requests, absent for notifications

    if method == "initialize":
        return jsonrpc.make_response(
            id_,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": SERVER_INFO,
            },
        )

    if method == "notifications/initialized":
        # The client confirms it's ready. Nothing to do but note it (to stderr -- see
        # stdio_transport.py) and return None: notifications never get a response.
        print("client sent notifications/initialized -- handshake complete", file=sys.stderr)
        return None

    if method == "tools/list":
        return jsonrpc.make_response(id_, {"tools": TOOLS})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        tool = next((t for t in TOOLS if t["name"] == tool_name), None)
        if tool is None:
            return jsonrpc.make_error(id_, jsonrpc.INVALID_PARAMS, f"Unknown tool '{tool_name}'")

        validation_error = _validate_args(tool["inputSchema"], arguments)
        if validation_error is not None:
            return jsonrpc.make_error(id_, jsonrpc.INVALID_PARAMS, validation_error)

        try:
            result = _call_tool(tool_name, arguments)
        except Exception as exc:  # a genuine unexpected server-side bug -> protocol error
            return jsonrpc.make_error(id_, jsonrpc.INTERNAL_ERROR, str(exc))
        return jsonrpc.make_response(id_, result)

    if method == "resources/list":
        return jsonrpc.make_response(id_, {"resources": RESOURCES})

    if method == "resources/read":
        uri = params.get("uri")
        if uri != "tasks://all":
            return jsonrpc.make_error(id_, jsonrpc.INVALID_PARAMS, f"Unknown resource '{uri}'")
        contents = [{"uri": uri, "mimeType": "text/plain", "text": task_store.list_tasks()}]
        return jsonrpc.make_response(id_, {"contents": contents})

    # Unknown method entirely.
    if id_ is None:
        return None  # an unknown *notification* is just ignored per spec, not an error
    return jsonrpc.make_error(id_, jsonrpc.METHOD_NOT_FOUND, f"Method not found: {method}")


def serve(in_stream: TextIO, out_stream: TextIO) -> int:
    """The read-dispatch-write loop, independent of what in_stream/out_stream actually are --
    a subprocess's piped stdin/stdout in normal use, or a pair of named pipes in background mode.
    """
    while True:
        try:
            message = read_message(in_stream)
        except Exception as exc:
            # Malformed JSON on the line -- id is unknown, so per spec we respond with id: null.
            write_message(out_stream, jsonrpc.make_error(None, jsonrpc.PARSE_ERROR, str(exc)))
            continue

        if message is None:
            print("[server] input closed, exiting", file=sys.stderr)
            return 0

        trace("<--", message)
        response = dispatch(message)
        if response is not None:
            trace("-->", response)
            write_message(out_stream, response)


def main() -> int:
    print(f"[server] starting, protocol {PROTOCOL_VERSION}", file=sys.stderr)

    if "--pipe-in" in sys.argv:
        pipe_in = sys.argv[sys.argv.index("--pipe-in") + 1]
        pipe_out = sys.argv[sys.argv.index("--pipe-out") + 1]
        # Open order matters: it must match MCPClient.connect()'s order exactly. Opening a FIFO
        # for reading blocks until some process opens the same path for writing (and vice versa),
        # so if the two sides opened their two pipes in swapped order, both would block forever
        # waiting on a pipe the other side hasn't gotten to yet. Server reads pipe_in first, then
        # writes pipe_out -- the client must write pipe_in first, then read pipe_out.
        print(f"[server] background mode, waiting for a client on {pipe_in}", file=sys.stderr)
        with open(pipe_in, "r") as in_stream, open(pipe_out, "w", buffering=1) as out_stream:
            print("[server] client connected", file=sys.stderr)
            return serve(in_stream, out_stream)

    return serve(sys.stdin, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
