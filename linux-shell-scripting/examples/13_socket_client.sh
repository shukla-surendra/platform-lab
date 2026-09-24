#!/usr/bin/env bash
#
# Demonstrates 13-sockets-between-machines.md: a TCP client using bash's built-in /dev/tcp.
#
# `exec 3<>/dev/tcp/HOST/PORT` is bash itself calling socket() + connect() and handing the
# result back as file descriptor 3. After that it's plain fd I/O: `>&3` is a write(),
# `<&3` is a read(), `3>&-` is close().
#
# Reads lines from stdin, sends each, prints the server's reply. Ctrl-D quits.
#
# Usage: ./13_socket_client.sh <server_ip> [port]     (default port 5000)
#
# Note: /dev/tcp is a bash feature, not a real file — it won't work in sh/dash.

set -uo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <server_ip> [port]" >&2
    exit 2
fi

host="$1"
port="${2:-5000}"

# socket() + connect() happen here; fd 3 is now the connection.
if ! exec 3<>"/dev/tcp/$host/$port"; then
    echo "could not connect to $host:$port" >&2
    exit 1
fi
echo "connected to $host:$port — type lines, Ctrl-D to quit"

while IFS= read -r line; do
    printf '%s\n' "$line" >&3            # write(3, ...)
    if ! IFS= read -r reply <&3; then     # read(3, ...); fails if the server hung up
        echo "server closed the connection" >&2
        break
    fi
    echo "reply from server: $reply"
done

exec 3>&-                                 # close(3)
