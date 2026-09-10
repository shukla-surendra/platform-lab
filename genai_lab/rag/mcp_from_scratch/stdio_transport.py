"""The stdio transport: how JSON-RPC messages actually travel over stdin/stdout.

MCP's stdio transport rule is simple and worth knowing exactly, because it's easy to violate by
accident: **one JSON-RPC message per line**, UTF-8, newline-delimited, and the JSON itself must
not contain an embedded literal newline (json.dumps without indent=... never does, so this is
automatic as long as you don't pretty-print onto the wire).

This is *not* the same framing HTTP or the Language Server Protocol (LSP) use -- LSP prefixes each
message with a `Content-Length: N\r\n\r\n` header so the reader knows exactly how many bytes to
read. MCP's stdio transport skips that: newline-delimited is simpler to implement (readline() is
enough) at the cost of requiring every message to fit on one line and never contain a raw
newline -- a real constraint if you were ever tempted to json.dumps(..., indent=2) onto the wire.

Also critical: **stdout is reserved for protocol messages only.** A server that does `print("debug
info")` for logging will corrupt the stream -- the client will try to json.loads() your debug
string as if it were a message and fail. Anything that isn't a JSON-RPC message must go to
stderr, which is exactly why every log/trace line in this project uses `file=sys.stderr`.
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO


def write_message(stream: TextIO, message: dict[str, Any]) -> None:
    """Write one JSON-RPC message as a single line and flush immediately -- the reader on the
    other end is blocked on readline() waiting for exactly this.
    """
    stream.write(json.dumps(message) + "\n")
    stream.flush()


def read_message(stream: TextIO) -> dict[str, Any] | None:
    """Read one line and parse it as JSON. Returns None on EOF (the other side closed the
    stream), which every read loop in this project treats as "shut down cleanly."
    """
    line = stream.readline()
    if line == "":
        return None
    return json.loads(line)


def trace(direction: str, message: dict[str, Any]) -> None:
    """Print the raw wire content to stderr, never stdout -- purely for teaching visibility.
    direction is "-->" for messages we're sending, "<--" for messages we're receiving.
    """
    print(f"{direction} {json.dumps(message)}", file=sys.stderr)
