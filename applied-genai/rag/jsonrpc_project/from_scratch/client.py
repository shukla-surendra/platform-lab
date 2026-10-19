#!/usr/bin/env python3
"""A from-scratch JSON-RPC 2.0 client: connects once, keeps the connection open across calls
(one TCP connection, many requests -- realistic for a client that isn't reconnecting per call).

Run against a live server.py:
  python client.py
  python client.py --port 9001
"""

from __future__ import annotations

import argparse
import socket

import jsonrpc
from socket_transport import read_message, write_message


class JSONRPCClient:
    def __init__(self, host: str, port: int):
        self._sock = socket.create_connection((host, port))
        self._rfile = self._sock.makefile("r")
        self._next_id = 1

    def call(self, method: str, params: dict | list | None = None):
        id_ = self._next_id
        self._next_id += 1
        write_message(self._sock, jsonrpc.make_request(id_, method, params))
        response = read_message(self._rfile)
        if response is None:
            raise ConnectionError("server closed the connection")
        if response.get("id") != id_:
            raise ConnectionError(f"expected response id {id_}, got {response.get('id')}")
        if "error" in response:
            err = response["error"]
            raise jsonrpc.RPCError(err["code"], err["message"], err.get("data"))
        return response["result"]

    def notify(self, method: str, params: dict | list | None = None) -> None:
        write_message(self._sock, jsonrpc.make_notification(method, params))
        # No response is sent or read -- that's the entire point of a notification.

    def call_batch(self, calls: list[tuple[str, dict | list | None]]) -> list:
        """Send several requests as one JSON-RPC batch (an array), get an array of responses
        back in one round trip. calls is a list of (method, params) tuples.
        """
        ids = list(range(self._next_id, self._next_id + len(calls)))
        self._next_id += len(calls)
        batch = [jsonrpc.make_request(id_, method, params) for id_, (method, params) in zip(ids, calls)]
        write_message(self._sock, batch)
        responses = read_message(self._rfile)
        by_id = {r["id"]: r for r in responses}
        return [by_id[id_] for id_ in ids]  # restore caller's original order

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
        except jsonrpc.RPCError as exc:
            print(f"caught expected RPCError: [{exc.code}] {exc.message}")

        print("\n=== protocol-level errors ===")
        try:
            client.call("no_such_method", {})
        except jsonrpc.RPCError as exc:
            print(f"caught expected RPCError: [{exc.code}] {exc.message}")
        try:
            client.call("add", {"x": 1})
        except jsonrpc.RPCError as exc:
            print(f"caught expected RPCError: [{exc.code}] {exc.message} ({exc.data})")

        print("\n=== batch request (one round trip, four calls) ===")
        results = client.call_batch([
            ("add", {"x": 1, "y": 1}),
            ("subtract", {"x": 10, "y": 4}),
            ("multiply", {"x": 3, "y": 3}),
            ("divide", {"x": 8, "y": 2}),
        ])
        for r in results:
            print(" ", r)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
