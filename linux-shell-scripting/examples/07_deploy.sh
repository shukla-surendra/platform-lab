#!/usr/bin/env bash
#
# Demonstrates 07-conditionals-and-control-flow.md: case dispatch plus a
# for loop inside the matched branch.
#
# Usage: ./07_deploy.sh {dev|staging|prod}

set -euo pipefail

env="${1:-}"

case "$env" in
    dev|staging|prod)
        echo "deploying to $env"
        for step in build test release; do
            echo "  step: $step ($env)"
        done
        ;;
    *)
        echo "usage: $0 {dev|staging|prod}" >&2
        exit 1
        ;;
esac
