#!/usr/bin/env python3
"""Block until a list of `host:port` TCP endpoints accept a connection, then exit 0. Used as a
dependency gate before the agent process starts -- `depends_on` in docker-compose only waits for
a container to *start*, not for the HTTP server or Ollama model inside it to actually be ready
to accept requests.

    python docker/wait_for.py ops-server:8001 knowledge-server:8002 ollama:11434
"""

from __future__ import annotations

import socket
import sys
import time


def wait_for(host: str, port: int, timeout: float = 120.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(1)
    raise SystemExit(f"Timed out waiting for {host}:{port}")


def main() -> None:
    for target in sys.argv[1:]:
        host, _, port = target.partition(":")
        print(f"Waiting for {host}:{port} ...", flush=True)
        wait_for(host, int(port))
    print("All dependencies are up.", flush=True)


if __name__ == "__main__":
    main()
