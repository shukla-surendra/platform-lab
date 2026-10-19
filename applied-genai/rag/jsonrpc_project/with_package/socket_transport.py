"""Identical to ../from_scratch/socket_transport.py -- copied rather than imported so this
subfolder is runnable standalone. Deliberately: neither `jsonrpcserver` nor `jsonrpcclient`
ship any transport of their own (they only build/parse/dispatch JSON-RPC *text*), so this file
is needed exactly as much in the "with package" version as in the from-scratch one. That's the
whole point of comparing them -- the package's value is entirely in jsonrpc.py's job, not this
file's.
"""

from __future__ import annotations

import json
import socket
from typing import Any


def write_message(sock: socket.socket, message: Any) -> None:
    sock.sendall((json.dumps(message) + "\n").encode("utf-8"))


def write_raw(sock: socket.socket, raw_json_text: str) -> None:
    """For the with_package server: jsonrpcserver.dispatch() already returns a JSON *string*,
    so there's no dict to re-serialize -- just frame the string that came back.
    """
    sock.sendall((raw_json_text + "\n").encode("utf-8"))


def read_message(rfile) -> Any | None:
    line = rfile.readline()
    if line == "":
        return None
    return json.loads(line)


def read_line(rfile) -> str | None:
    """For the with_package server: jsonrpcserver.dispatch() takes the raw JSON text directly
    (it does its own parsing), so there's no need to json.loads() here at all.
    """
    line = rfile.readline()
    return None if line == "" else line
