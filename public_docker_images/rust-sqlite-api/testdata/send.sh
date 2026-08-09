#!/usr/bin/env bash
# Send the sample OTLP payloads, substituting real timestamps so the data lands
# inside any `since=` window you query with. Fixed timestamps in the fixtures
# would fall outside retention within a few days and silently disappear.
set -euo pipefail

ENDPOINT="${ENDPOINT:-http://localhost:8080}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

now_nanos() {
  # macOS date has no %N; python is the portable way to nanosecond precision.
  python3 -c 'import time; print(int(time.time()*1e9))'
}

T0=$(now_nanos)
T1=$((T0 + 12000000))    # +12ms
T2=$((T0 + 45000000))    # +45ms
T3=$((T0 + 91000000))    # +91ms  → root span is 91ms wide

render() {
  sed -e "s/__T0__/$T0/g" -e "s/__T1__/$T1/g" -e "s/__T2__/$T2/g" -e "s/__T3__/$T3/g" "$1"
}

post() {
  local path="$1" file="$2"
  printf '%-14s → ' "$path"
  render "$HERE/$file" | curl -sS -X POST "$ENDPOINT$path" \
    -H 'content-type: application/json' --data-binary @-
  printf '\n'
}

post /v1/traces  traces.json
post /v1/logs    logs.json
post /v1/metrics metrics.json

echo "sent. flush interval is 250ms — give it a moment before querying."
