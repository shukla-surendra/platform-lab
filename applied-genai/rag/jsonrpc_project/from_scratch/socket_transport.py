"""Newline-delimited JSON over a raw TCP socket -- the "truck" carrying jsonrpc.py's "envelope."

Same framing rule as ../../mcp_from_scratch/stdio_transport.py (one JSON message per line, no
embedded newlines), deliberately, to make the point from
../../docs/Agentic_Concepts/15-jsonrpc-explained.md concrete: JSON-RPC doesn't care whether the
bytes travel over a subprocess's stdin/stdout pipes or a network socket. Only this file changes
between the two projects; jsonrpc.py's message shapes are identical.

Uses `socket.makefile()` to get a buffered, line-oriented file object out of a raw socket -- the
standard library trick that means read_message/write_message below are almost verbatim the same
two functions as the stdio version.
"""

from __future__ import annotations

import json
import socket
from typing import Any


def write_message(sock: socket.socket, message: Any) -> None:
    sock.sendall((json.dumps(message) + "\n").encode("utf-8"))


def read_message(rfile) -> Any | None:
    """rfile is a buffered file object from sock.makefile('r'). Returns None on a closed
    connection (EOF), same convention as the stdio version.
    """
    line = rfile.readline()
    if line == "":
        return None
    return json.loads(line)
