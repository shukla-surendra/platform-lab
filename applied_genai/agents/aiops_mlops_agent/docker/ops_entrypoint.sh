#!/bin/sh
# Seed the shared world_state.json exactly once -- only if this volume hasn't been seeded yet.
# A restart of this container (e.g. `docker compose restart ops-server` to flip APPLY_CHANGES)
# must NOT wipe accumulated incident/ticket state, so this checks for the file rather than
# unconditionally running seed.py the way local dev's `make reset` does.
set -e

if [ ! -f "$STATE_FILE" ]; then
    echo "No world_state.json at $STATE_FILE -- seeding baseline." >&2
    python seed.py
fi

exec python mcp_servers/ops_server.py
