#!/usr/bin/env bash
# Starts a server, runs its client demo against it, and guarantees the server is stopped
# afterward (even if the client crashes) via `trap`. Two terminals showing the server and client
# side by side is the more instructive way to run this project once -- this script exists for a
# one-command sanity check and for `make demo-scratch` / `make demo-package`.
#
# Usage: ./run_demo.sh from_scratch|with_package [port]
set -euo pipefail

VARIANT="${1:?usage: run_demo.sh from_scratch|with_package [port]}"
PORT="${2:-9100}"

cd "$(dirname "$0")/$VARIANT"

python3 server.py --port "$PORT" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true' EXIT

sleep 1
python3 client.py --port "$PORT"
