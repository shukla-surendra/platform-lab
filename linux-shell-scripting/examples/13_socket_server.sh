#!/usr/bin/bash
#
# Demonstrates 13-sockets-between-machines.md: a TCP echo server built from shell + nc.
#
# Bash has no listen()/accept() of its own, so `nc -l` does the server-side syscalls
# (socket -> bind -> listen -> accept). The shell's job is the plumbing around it:
# a named pipe carries our replies back into nc, so what nc receives is echoed to the client.
#
# nc serves ONE connection, then exits — the `while true` loop re-listens for the next client.
#
# Usage: ./13_socket_server.sh [port]        (default port 5000)
#
# Needs BSD-style nc (macOS, and Ubuntu/Debian's default netcat-openbsd on WSL).
# If your nc is netcat-traditional, change `nc -l "$port"` to `nc -l -p "$port"`.

set -uo pipefail

port="${1:-5000}"

fifo="$(mktemp -u)"
mkfifo "$fifo"
trap 'rm -f "$fifo"' EXIT

echo "listening on 0.0.0.0:$port  (Ctrl-C to stop)"

while true; do
    # `nc -l` reads the reply pipe as its stdin (=> bytes sent TO the client) and writes what
    # the client sent to its stdout, which the loop below turns into a reply.
    nc -l "$port" < "$fifo" | while IFS= read -r line; do
        echo "received: $line" >&2
        echo "echo: $line"
    done > "$fifo"
    echo "client disconnected" >&2
done
