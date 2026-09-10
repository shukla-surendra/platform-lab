#!/usr/bin/env python3
"""The same calculator service as ../from_scratch/server.py, this time using the `jsonrpcserver`
package for message parsing, validation, and dispatch. Compare this file to
../from_scratch/server.py + jsonrpc.py directly -- same methods, same error behavior, a fraction
of the code, because message shape validation, batch handling, and error-code selection are the
package's job now instead of ours.

Run:
  python server.py                  # listens on 127.0.0.1:9000
  python server.py --port 9001
"""

from __future__ import annotations

import argparse
import socketserver
import sys

from jsonrpcserver import Error, Success, dispatch, method

from socket_transport import read_line, write_raw

# -32000 to -32099 are reserved for implementation-defined server errors -- same code chosen in
# ../from_scratch/jsonrpc.py, so the two servers' wire output for this case is identical.
DIVISION_BY_ZERO = -32000


@method
def add(x: float, y: float):
    return Success(x + y)


@method
def subtract(x: float, y: float):
    return Success(x - y)


@method
def multiply(x: float, y: float):
    return Success(x * y)


@method
def divide(x: float, y: float):
    if y == 0:
        return Error(DIVISION_BY_ZERO, "Division by zero")
    return Success(x / y)


@method
def log(message: str):
    print(f"[server log] {message}", file=sys.stderr)
    return Success(None)  # discarded when called as a notification, same as the from-scratch version


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        peer = self.client_address
        print(f"[server] connection from {peer}", file=sys.stderr)
        rfile = self.request.makefile("r")  # text mode -- see ../from_scratch/server.py's note
        while True:
            line = read_line(rfile)
            if line is None:
                print(f"[server] {peer} disconnected", file=sys.stderr)
                return

            print(f"[server] <- {line.strip()}", file=sys.stderr)
            response = dispatch(line)  # jsonrpcserver parses, validates, routes, and serializes
            if response:  # "" for a notification -- nothing to send back
                print(f"[server] -> {response}", file=sys.stderr)
                write_raw(self.request, response)


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
