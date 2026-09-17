#!/usr/bin/env bash
#
# Demonstrates 08-functions-and-arguments.md: a function plus getopts
# flag parsing.
#
# Usage: ./08_greet.sh [-n name] [-c count]

set -euo pipefail

name="world"
count=1

usage() {
    echo "Usage: $0 [-n name] [-c count]" >&2
    exit 1
}

while getopts "n:c:h" opt; do
    case "$opt" in
        n) name="$OPTARG" ;;
        c) count="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

greet() {
    local who="$1"
    echo "Hello, $who"
}

for ((i = 0; i < count; i++)); do
    greet "$name"
done
