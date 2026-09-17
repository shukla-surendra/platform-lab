#!/usr/bin/env bash
#
# Demonstrates 11-json-and-cron.md: jq basics, plus what a crontab line
# for this script would look like.

set -uo pipefail

echo "=== jq on a literal JSON string (no network needed) ==="
echo '{"name":"web1","status":"healthy","port":8080}' | jq '.name'
echo '{"name":"web1","status":"healthy","port":8080}' | jq -r '.name'

echo
echo "=== jq -e for a boolean check, usable directly in an if ==="
if echo '{"status":"ok"}' | jq -e '.status == "ok"' >/dev/null; then
    echo "status is ok"
fi

echo
echo "=== jq on a live API (needs network — skips cleanly if offline) ==="
tmp_json="$(mktemp)"
trap 'rm -f "$tmp_json"' EXIT
if curl -s --max-time 3 https://api.github.com/repos/torvalds/linux -o "$tmp_json" 2>/dev/null; then
    jq -r '.full_name, .language, .stargazers_count' "$tmp_json"
else
    echo "(no network reachable — skipped)"
fi

echo
echo "=== the crontab line this script would use, for reference ==="
echo "*/15 * * * * $(cd "$(dirname "$0")" && pwd)/$(basename "$0") >> /tmp/jq_cron_demo.log 2>&1"
