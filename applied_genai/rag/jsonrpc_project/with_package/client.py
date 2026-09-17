#!/usr/bin/env python3
"""The same demo as ../from_scratch/client.py, this time built on the `jsonrpcclient` package
for request/notification construction and response parsing. Compare directly against
../from_scratch/client.py.

Run against a live server.py:
  python client.py
  python client.py --port 9001
"""

from __future__ import annotations

import argparse
import json
import socket

from jsonrpcclient import Error, Ok, notification, parse, parse_json, request

from socket_transport import write_message


class JSONRPCClient:
    def __init__(self, host: str, port: int):
        self._sock = socket.create_connection((host, port))
        self._rfile = self._sock.makefile("r")

    def call(self, method: str, params: dict | None = None):
        req = request(method, params=params)  # {"jsonrpc": "2.0", "method": ..., "id": <auto>}
        write_message(self._sock, req)
        line = self._rfile.readline()
        if line == "":
            raise ConnectionError("server closed the connection")
        result = parse(json.loads(line))
        if isinstance(result, Error):
            raise RuntimeError(f"[{result.code}] {result.message}" + (f" ({result.data})" if result.data else ""))
        return result.result  # Ok(result=..., id=...)

    def notify(self, method: str, params: dict | None = None) -> None:
        write_message(self._sock, notification(method, params=params))
        # No response is sent or read.

    def call_batch(self, calls: list[tuple[str, dict | None]]) -> list:
        requests = [request(method, params=params) for method, params in calls]
        write_message(self._sock, requests)  # a list -- jsonrpcserver.dispatch() treats this as a batch
        line = self._rfile.readline()
        if line == "":
            raise ConnectionError("server closed the connection")
        return list(parse_json(line))  # a map of Ok/Error, one per request, in order

    def close(self) -> None:
        self._sock.close()

    def __enter__(self) -> "JSONRPCClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    with JSONRPCClient(args.host, args.port) as client:
        print("=== single calls ===")
        print("add(2, 3) =", client.call("add", {"x": 2, "y": 3}))
        print("multiply(6, 7) =", client.call("multiply", {"x": 6, "y": 7}))

        print("\n=== notification (no reply expected) ===")
        client.notify("log", {"message": "client says hello"})

        print("\n=== application-level error ===")
        try:
            client.call("divide", {"x": 1, "y": 0})
        except RuntimeError as exc:
            print(f"caught expected error: {exc}")

        print("\n=== protocol-level errors ===")
        try:
            client.call("no_such_method", {})
        except RuntimeError as exc:
            print(f"caught expected error: {exc}")
        try:
            client.call("add", {"x": 1})
        except RuntimeError as exc:
            print(f"caught expected error: {exc}")

        print("\n=== batch request (one round trip, four calls) ===")
        results = client.call_batch([
            ("add", {"x": 1, "y": 1}),
            ("subtract", {"x": 10, "y": 4}),
            ("multiply", {"x": 3, "y": 3}),
            ("divide", {"x": 8, "y": 2}),
        ])
        for r in results:
            label = "Ok" if isinstance(r, Ok) else "Error"
            print(f"  {label}: {r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
