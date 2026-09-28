#!/usr/bin/env bash
# End-to-end smoke test against a RUNNING server. Exits non-zero on the first
# unexpected status code.
#   ./scripts/smoke.sh http://localhost:8081
set -euo pipefail
BASE="${1:-http://localhost:8081}"

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

# req METHOD PATH EXPECTED_STATUS [JSON_BODY] -- prints body, sets $BODY
req() {
  local method=$1 path=$2 want=$3 data=${4:-}
  local args=(-s -o /tmp/smoke_body -w '%{http_code}' -X "$method" "$BASE$path")
  [[ -n "$data" ]] && args+=(-H 'Content-Type: application/json' -d "$data")
  local got; got=$(curl "${args[@]}")
  BODY=$(cat /tmp/smoke_body)
  echo "$method $path -> $got  $BODY"
  [[ "$got" == "$want" ]] || { echo "   expected $want"; exit 1; }
}

step "health"
req GET /healthz 200
req GET /readyz 200

step "create"
req POST /v1/tasks 201 '{"title":"Write the README","priority":2}'
ID=$(sed -E 's/.*"id":([0-9]+).*/\1/' <<<"$BODY")
req POST /v1/tasks 201 '{"title":"Add pagination","due_at":"2030-01-01T09:00:00Z"}'

step "read"
req GET "/v1/tasks/$ID" 200
req GET "/v1/tasks?limit=1" 200

step "partial update"
req PATCH "/v1/tasks/$ID" 200 '{"status":"in_progress"}'
req GET "/v1/tasks?status=in_progress" 200

step "errors"
req POST /v1/tasks 422 '{"title":"","priority":9}'
req POST /v1/tasks 400 '{"titel":"typo"}'
req GET /v1/tasks/999999 404

step "delete"
req DELETE "/v1/tasks/$ID" 204
req GET "/v1/tasks/$ID" 404

echo -e "\nsmoke test passed"
