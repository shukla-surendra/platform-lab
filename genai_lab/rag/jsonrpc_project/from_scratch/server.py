#!/usr/bin/env python3
"""A from-scratch JSON-RPC 2.0 server: a small calculator service, no package -- only jsonrpc.py
(message shapes + dispatch) and socket_transport.py (framing) plus the standard library's
`socketserver` for the TCP accept-loop plumbing (not a JSON-RPC library -- socketserver just
saves writing accept()/thread-per-connection by hand, the same role FastAPI/Flask would play for
an HTTP transport).

Methods: add, subtract, multiply, divide (a deliberate application-level error on divide-by-zero,
not a protocol error -- see jsonrpc.py's RPCError), and log (a notification-only method with no
meaningful return value, to demonstrate notifications with a real use case: "tell the server
something, don't wait for a reply").

Run:
  python server.py                  # listens on 127.0.0.1:9000
  python server.py --port 9001
"""

from __future__ import annotations

import argparse
import socketserver
import sys

import jsonrpc
from socket_transport import read_message, write_message


@jsonrpc.register("add")
def add(x: float, y: float) -> float:
    return x + y


@jsonrpc.register("subtract")
def subtract(x: float, y: float) -> float:
    return x - y


@jsonrpc.register("multiply")
def multiply(x: float, y: float) -> float:
    return x * y


@jsonrpc.register("divide")
def divide(x: float, y: float) -> float:
    if y == 0:
        raise jsonrpc.RPCError(jsonrpc.SERVER_ERROR, "Division by zero")
    return x / y


@jsonrpc.register("log")
def log(message: str) -> None:
    # Only ever reached via a notification (no id), so its return value is discarded by
    # dispatch_one() regardless -- it exists purely for its side effect.
    print(f"[server log] {message}", file=sys.stderr)


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        peer = self.client_address
        print(f"[server] connection from {peer}", file=sys.stderr)
        # self.rfile is binary by default (StreamRequestHandler's rbufsize mode) -- readline()
        # would return bytes, and read_message()'s text-mode EOF check ("" ) would never match
        # b"". Wrap our own text-mode file object over the same socket instead, matching how
        # client.py does it.
        rfile = self.request.makefile("r")
        while True:
            try:
                message = read_message(rfile)
            except Exception as exc:
                error = jsonrpc.make_error(None, jsonrpc.PARSE_ERROR, "Parse error", str(exc))
                write_message(self.request, error)
                continue

            if message is None:
                print(f"[server] {peer} disconnected", file=sys.stderr)
                return

            print(f"[server] <- {message}", file=sys.stderr)
            response = jsonrpc.dispatch(message)
            if response is not None:
                print(f"[server] -> {response}", file=sys.stderr)
                write_message(self.request, response)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    with socketserver.ThreadingTCPServer((args.host, args.port), Handler) as server:
        server.allow_reuse_address = True
        print(f"[server] listening on {args.host}:{args.port}", file=sys.stderr)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[server] shutting down", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
