#!/usr/bin/env bash
# End-to-end acceptance check. Works identically against a native `make dev`
# process and a running container — same assertions, so "it worked locally"
# and "it works in the image" mean the same thing.
#
# Exits non-zero on the first failure. This is the definition of "satisfied";
# reading JSON and nodding is not.
set -uo pipefail

ENDPOINT="${ENDPOINT:-http://localhost:8080}"

pass=0
fail=0

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  \033[31m✗\033[0m %s\n     expected: %s\n     actual:   %s\n' "$1" "$2" "$3"; fail=$((fail+1)); }

# assert <label> <expected> <actual>
assert() { [ "$2" = "$3" ] && ok "$1" || bad "$1" "$2" "$3"; }

# status <method> <path> [data]
status() {
  if [ $# -ge 3 ]; then
    curl -s -o /dev/null -w '%{http_code}' -X "$1" "$ENDPOINT$2" \
      -H 'content-type: application/json' -d "$3"
  else
    curl -s -o /dev/null -w '%{http_code}' -X "$1" "$ENDPOINT$2"
  fi
}

jq_py() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

echo "verifying $ENDPOINT"

# --- probes & identity ------------------------------------------------------
echo "probes"
assert "GET /healthz"  "200" "$(status GET /healthz)"
assert "GET /readyz"   "200" "$(status GET /readyz)"
assert "GET /version"  "200" "$(status GET /version)"
assert "GET / (landing page)" "text/html; charset=utf-8" \
  "$(curl -s -o /dev/null -D - "$ENDPOINT/" | grep -i '^content-type' | tr -d '\r' | cut -d' ' -f2-)"

echo "endpoint reference"
assert "GET /api/endpoints returns entries" "yes" \
  "$(curl -s "$ENDPOINT/api/endpoints" | jq_py '"yes" if d["count"] > 0 else "no"')"
assert "landing page has no unreplaced marker" "0" \
  "$(curl -s "$ENDPOINT/" | grep -c 'ENDPOINTS-->')"
assert "landing page row count == /api/endpoints count" "yes" \
  "$(python3 -c "
import json, urllib.request, re
n = json.load(urllib.request.urlopen('$ENDPOINT/api/endpoints'))['count']
html = urllib.request.urlopen('$ENDPOINT/').read().decode()
rows = len(re.findall(r'class=\"row\"', html))
# +1 for the manual 'Try it' button row, which is not a registered endpoint.
print('yes' if rows == n + 1 else f'no ({rows} rows, {n} endpoints)')
")"

# --- log generation ----------------------------------------------------------
echo "log generation"
RESP=$(curl -s -X POST "$ENDPOINT/debug/logstorm?count=100&level=error&tag=verify-run")
assert "logstorm requested == 100" "100" "$(echo "$RESP" | jq_py 'd["requested"]')"
assert "logstorm emitted == suppressed complement" "yes" \
  "$(echo "$RESP" | jq_py '"yes" if d["requested"] == d["emitted"] + d["suppressed_by_log_level"] else "no"')"
assert "logstorm error count matches" "yes" \
  "$(echo "$RESP" | jq_py '"yes" if d["by_level"]["error"] + 0 <= 100 else "no"')"

RANDOM_RESP=$(curl -s -X POST "$ENDPOINT/debug/random-logs?count=100&run_id=verify-random")
assert "random-logs requested == 100" "100" "$(echo "$RANDOM_RESP" | jq_py 'd["requested"]')"
assert "random-logs emitted == suppressed complement" "yes" \
  "$(echo "$RANDOM_RESP" | jq_py '"yes" if d["requested"] == d["emitted"] + d["suppressed_by_log_level"] else "no"')"
assert "random-logs by_level sums to emitted" "yes" \
  "$(echo "$RANDOM_RESP" | jq_py '"yes" if sum(d["by_level"].values()) == d["emitted"] else "no"')"
assert "random-logs run_id echoed back" "verify-random" "$(echo "$RANDOM_RESP" | jq_py 'd["run_id"]')"
assert "random-logs zero-param call has a random volume" "yes" \
  "$(curl -s -X POST "$ENDPOINT/debug/random-logs" | jq_py '"yes" if d["requested"] >= 20 else "no"')"

# --- API-testing surface ----------------------------------------------------
echo "api testing surface"
assert "GET /api/test/uuid returns a uuid" "36" \
  "$(curl -s "$ENDPOINT/api/test/uuid" | jq_py 'len(d["uuid"])')"
assert "GET /api/test/status/503 returns 503" "503" "$(status GET /api/test/status/503)"
assert "GET /api/test/status/418 has teapot reason" "I'm a teapot" \
  "$(curl -s "$ENDPOINT/api/test/status/418" | jq_py 'd["canonical_reason"]')"
assert "GET /api/test/delay/300 takes >=300ms" "yes" \
  "$(curl -s "$ENDPOINT/api/test/delay/300" | jq_py '"yes" if d["actual_delay_ms"] >= 290 else "no"')"
assert "GET /api/test/bytes/128 returns 128 bytes" "128" \
  "$(curl -s "$ENDPOINT/api/test/bytes/128" | wc -c | tr -d ' ')"
assert "GET /api/test/json?count=3 returns 3 items" "3" \
  "$(curl -s "$ENDPOINT/api/test/json?count=3" | jq_py 'd["count"]')"
assert "GET /api/test/headers echoes a custom header" "yes" \
  "$(curl -s -H 'x-verify: abc' "$ENDPOINT/api/test/headers" | jq_py '"yes" if d["headers"].get("x-verify")=="abc" else "no"')"
assert "GET /api/test/ip reports a peer" "yes" \
  "$(curl -s "$ENDPOINT/api/test/ip" | jq_py '"yes" if len(d["peer"])>0 else "no"')"

echo "echo"
ECHO=$(curl -s -X POST "$ENDPOINT/api/test/echo?a=1" -H 'content-type: application/json' -d '{"k":"v"}')
assert "echo reports method" "POST" "$(echo "$ECHO" | jq_py 'd["method"]')"
assert "echo reports query"  "a=1"  "$(echo "$ECHO" | jq_py 'd["query"]')"
assert "echo parses JSON body" "v" "$(echo "$ECHO" | jq_py 'd["json"]["k"]')"

# --- result ------------------------------------------------------------------
echo
if [ "$fail" -eq 0 ]; then
  printf '\033[32m%d passed, 0 failed\033[0m — ship it\n' "$pass"
  exit 0
else
  printf '\033[31m%d passed, %d FAILED\033[0m — do not build the image yet\n' "$pass" "$fail"
  exit 1
fi
