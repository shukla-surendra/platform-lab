"""JSON-RPC 2.0 message construction, parsing, and dispatch — implemented directly from the spec
(https://www.jsonrpc.org/specification), no package. See ../../docs/Agentic_Concepts/15-jsonrpc-explained.md
for the plain-English tour this code is the "see it for real" companion to.

Unlike ../../mcp_from_scratch/jsonrpc.py (which only needed single request/notification/response
shapes because MCP doesn't use it), this version also implements **batching** — sending an array
of requests in one message and getting an array of responses back — since that's part of base
JSON-RPC 2.0 and this project isn't constrained by MCP's narrower usage of the spec.
"""

from __future__ import annotations

from typing import Any, Callable

JSONRPC_VERSION = "2.0"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
# -32000 to -32099 are reserved for implementation-defined "server error" codes -- this project
# uses -32000 specifically for "division by zero", an application-level failure, not a malformed
# request. See dispatch()'s docstring for why that distinction matters.
SERVER_ERROR = -32000


class RPCError(Exception):
    """Raised by a registered method to signal a JSON-RPC error response (not a Python bug) --
    e.g. divide() raises RPCError(SERVER_ERROR, "Division by zero") deliberately.
    """

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def make_request(id_: int, method: str, params: Any = None) -> dict[str, Any]:
    message: dict[str, Any] = {"jsonrpc": JSONRPC_VERSION, "id": id_, "method": method}
    if params is not None:
        message["params"] = params
    return message


def make_notification(method: str, params: Any = None) -> dict[str, Any]:
    message: dict[str, Any] = {"jsonrpc": JSONRPC_VERSION, "method": method}
    if params is not None:
        message["params"] = params
    return message


def make_response(id_: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": id_, "result": result}


def make_error(id_: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": id_, "error": error}


def is_notification(message: dict[str, Any]) -> bool:
    return "method" in message and "id" not in message


# --- a tiny method registry + dispatcher, the hand-rolled equivalent of jsonrpcserver's @method
# and dispatch() ---------------------------------------------------------------------------------

_METHODS: dict[str, Callable[..., Any]] = {}


def register(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: @register("add") def add(x, y): return x + y -- deliberately mirrors
    jsonrpcserver's @method decorator's ergonomics so the with_package/ version reads almost
    identically, with only the decorator's origin different.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        _METHODS[name] = func
        return func

    return decorator


def dispatch_one(message: dict[str, Any]) -> dict[str, Any] | None:
    """Handle exactly one request or notification. Returns a response dict, or None if the
    message was a notification (no reply expected) or was itself malformed in a way that
    forbids a reply (per spec, a notification never gets a response even if it fails).
    """
    method_name = message.get("method")
    params = message.get("params", {})
    id_ = message.get("id")
    is_notif = is_notification(message)

    func = _METHODS.get(method_name)
    if func is None:
        return None if is_notif else make_error(id_, METHOD_NOT_FOUND, "Method not found", method_name)

    try:
        if isinstance(params, dict):
            result = func(**params)
        elif isinstance(params, list):
            result = func(*params)
        else:
            result = func()
    except RPCError as exc:
        return None if is_notif else make_error(id_, exc.code, exc.message, exc.data)
    except TypeError as exc:
        # A Python-level "missing/unexpected argument" -- the from-scratch equivalent of
        # jsonrpcserver's automatic Invalid params detection.
        return None if is_notif else make_error(id_, INVALID_PARAMS, "Invalid params", str(exc))
    except Exception as exc:  # a genuine bug in the method itself
        return None if is_notif else make_error(id_, INTERNAL_ERROR, "Internal error", str(exc))

    return None if is_notif else make_response(id_, result)


def dispatch(payload: Any) -> Any:
    """Handle a single message OR a batch (a JSON array of messages), per spec. Returns a single
    response dict, a list of response dicts (batch), or None (nothing to send back -- e.g. a lone
    notification, or a batch containing only notifications).
    """
    if isinstance(payload, list):
        if not payload:
            return make_error(None, INVALID_REQUEST, "Invalid Request", "empty batch")
        responses = [r for r in (dispatch_one(m) for m in payload) if r is not None]
        return responses or None

    return dispatch_one(payload)
