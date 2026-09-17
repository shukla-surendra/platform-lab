"""JSON-RPC 2.0 message construction and validation — the wire format MCP is built on top of.

MCP does not invent its own message format. Every MCP request, response, and notification is a
JSON-RPC 2.0 message (https://www.jsonrpc.org/specification). This module has nothing MCP-specific
in it at all; it would look the same if you were implementing any other JSON-RPC-based protocol.

The four message shapes:
    request:      {"jsonrpc": "2.0", "id": 1, "method": "...", "params": {...}}
    notification: {"jsonrpc": "2.0", "method": "...", "params": {...}}            (no "id" -- no reply expected)
    response:     {"jsonrpc": "2.0", "id": 1, "result": {...}}
    error:        {"jsonrpc": "2.0", "id": 1, "error": {"code": ..., "message": ...}}

A message is a *request* if it has an "id" and a "method". It's a *notification* if it has a
"method" but no "id" -- the absence of "id" is exactly what tells the receiver "don't bother
replying." A message is a *response* (success or error) if it has an "id" and either "result" or
"error", but no "method".
"""

from __future__ import annotations

from typing import Any

JSONRPC_VERSION = "2.0"

# Standard JSON-RPC 2.0 error codes (the spec reserves -32768 to -32000).
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def make_request(id_: int, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    message = {"jsonrpc": JSONRPC_VERSION, "id": id_, "method": method}
    if params is not None:
        message["params"] = params
    return message


def make_notification(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    message = {"jsonrpc": JSONRPC_VERSION, "method": method}
    if params is not None:
        message["params"] = params
    return message


def make_response(id_: int, result: Any) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": id_, "result": result}


def make_error(id_: int | None, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": id_, "error": error}


def is_request(message: dict[str, Any]) -> bool:
    return "method" in message and "id" in message


def is_notification(message: dict[str, Any]) -> bool:
    return "method" in message and "id" not in message


def is_success_response(message: dict[str, Any]) -> bool:
    return "result" in message and "id" in message


def is_error_response(message: dict[str, Any]) -> bool:
    return "error" in message and "id" in message


if __name__ == "__main__":
    # Run this file directly to see the four shapes with no MCP involved at all:
    #   python jsonrpc.py
    import json

    examples = [
        ("request", make_request(1, "tools/list")),
        ("notification", make_notification("notifications/initialized")),
        ("success response", make_response(1, {"tools": []})),
        ("error response", make_error(1, METHOD_NOT_FOUND, "Method not found")),
    ]
    for label, message in examples:
        print(f"{label:18s} {json.dumps(message)}")
