"""A from-scratch MCP client: spawns a server as a subprocess, speaks JSON-RPC over its stdin/
stdout, and wraps the handshake + tool/resource calls in a small Python API. This is the same
role `langchain_mcp_adapters.client.MultiServerMCPClient` plays in Chapter 12's "leveling up"
snippet -- here it's ~80 lines of stdlib `subprocess` + `json` instead of a dependency.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from genai_lab.rag.mcp_from_scratch.stdio_transport import read_message, trace, write_message

PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "mcp-from-scratch-client", "version": "0.1.0"}


class MCPError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class MCPClient:
    """Owns one server subprocess for the lifetime of the client (or, via connect(), attaches to
    an already-running background server instead of spawning one). Not thread-safe, not meant to
    be -- one request is in flight at a time, matching how a synchronous tool-calling agent loop
    actually uses it.
    """

    def __init__(self, command: list[str], verbose: bool = True):
        self._verbose = verbose
        self._next_id = 1
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,  # inherit -- the server's [server]/trace lines print directly, interleaved
            text=True,
            bufsize=1,  # line-buffered, required so write_message's flush is actually meaningful
        )
        self._in = self._process.stdin
        self._out = self._process.stdout

    @classmethod
    def connect(cls, request_pipe: str, response_pipe: str, verbose: bool = True) -> "MCPClient":
        """Attach to a server already running in the background (see `make server-bg`) via a pair
        of named pipes, instead of spawning a new server subprocess. Used from the Jupyter demo so
        the server's state (tasks.json) and process persist across notebook cells and kernel
        restarts, rather than resetting every time a fresh MCPClient(...) would spawn one.

        Open order matters and must mirror mcp_server.py's background mode exactly: request_pipe
        opened for writing first, then response_pipe for reading. Opening a FIFO end blocks until
        the complementary end (the server's read of request_pipe, its write of response_pipe) is
        opened by the other process -- swapped order on either side deadlocks both processes
        waiting on pipes neither has gotten to yet.
        """
        self = cls.__new__(cls)
        self._verbose = verbose
        self._next_id = 1
        self._process = None
        self._in = open(request_pipe, "w", buffering=1)
        self._out = open(response_pipe, "r")
        return self

    # --- wire-level plumbing ---------------------------------------------------------------

    def _send(self, message: dict[str, Any]) -> None:
        if self._verbose:
            trace("-->", message)
        write_message(self._in, message)

    def _recv(self) -> dict[str, Any]:
        message = read_message(self._out)
        if message is None:
            raise ConnectionError("server closed its output unexpectedly")
        if self._verbose:
            trace("<--", message)
        return message

    def _request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        id_ = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": id_, "method": method, **({"params": params} if params else {})})

        response = self._recv()
        if response.get("id") != id_:
            raise ConnectionError(f"expected response id {id_}, got {response.get('id')}")
        if "error" in response:
            raise MCPError(response["error"]["code"], response["error"]["message"])
        return response["result"]

    def _notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, **({"params": params} if params else {})})

    # --- MCP lifecycle -----------------------------------------------------------------------

    def initialize(self) -> dict[str, Any]:
        result = self._request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": CLIENT_INFO},
        )
        # The handshake isn't done until this notification is sent -- the server is told "I got
        # your capabilities, I'm ready for real requests now."
        self._notify("notifications/initialized")
        return result

    # --- tools ---------------------------------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        return self._request("tools/list")["tools"]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        result = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        text = "\n".join(block["text"] for block in result["content"] if block["type"] == "text")
        if result.get("isError"):
            raise RuntimeError(f"tool '{name}' reported an error: {text}")
        return text

    # --- resources -------------------------------------------------------------------------

    def list_resources(self) -> list[dict[str, Any]]:
        return self._request("resources/list")["resources"]

    def read_resource(self, uri: str) -> str:
        result = self._request("resources/read", {"uri": uri})
        return "\n".join(c["text"] for c in result["contents"])

    # --- lifecycle -----------------------------------------------------------------------------

    def close(self) -> None:
        """Closing self._in makes the server see EOF and exit (same shutdown convention either
        way -- see mcp_server.py's serve()). For a connect()-ed background server this means
        close() ends that server process too, not just this client's view of it; start a fresh one
        with `make server-bg` for the next session.
        """
        self._in.close()
        if self._process is not None:
            self._process.wait(timeout=5)
        else:
            self._out.close()

    def __enter__(self) -> "MCPClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


if __name__ == "__main__":
    # A tiny smoke test independent of demo.py: spawn the server, say hello, hang up.
    with MCPClient([sys.executable, "mcp_server.py"]) as client:
        info = client.initialize()
        print("initialized against:", info["serverInfo"], file=sys.stderr)
