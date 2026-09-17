#!/usr/bin/env bash
#
# Demonstrates 02-filesystem-and-permissions.md: creating files/dirs and
# watching `ls -la` output change as `chmod` changes.
#
# Usage: ./02_filesystem_and_permissions.sh [practice_dir]

set -uo pipefail

practice_dir="${1:-$HOME/practice}"
echo "Using practice directory: $practice_dir"

mkdir -p "$practice_dir"/{a,b,c}
touch "$practice_dir/deploy.sh"

echo
echo "=== before chmod ==="
ls -la "$practice_dir/deploy.sh"

chmod +x "$practice_dir/deploy.sh"
echo
echo "=== after chmod +x ==="
ls -la "$practice_dir/deploy.sh"

chmod 644 "$practice_dir/deploy.sh"
echo
echo "=== after chmod 644 ==="
ls -la "$practice_dir/deploy.sh"

echo
echo "=== full directory listing ==="
ls -la "$practice_dir"
