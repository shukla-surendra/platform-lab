#!/usr/bin/env bash
#
# Demonstrates 09-arrays-strings-and-io.md: an associative array plus
# backgrounded jobs + wait. Expect every port to report DOWN unless you
# have something actually listening on 8000/8001/8002 locally — that's
# fine, the point is the array + parallel-check pattern, not the result.

set -uo pipefail

declare -A env_ports
env_ports[dev]=8000
env_ports[staging]=8001
env_ports[prod]=8002

check_port() {
    local env="$1"
    local port="$2"
    if curl -sf --max-time 2 "http://localhost:$port" >/dev/null 2>&1; then
        echo "OK   $env (port $port)"
    else
        echo "DOWN $env (port $port)"
    fi
}

for env in "${!env_ports[@]}"; do
    check_port "$env" "${env_ports[$env]}" &
done
wait
