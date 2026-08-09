#!/usr/bin/env bash
# End-to-end acceptance check. Works identically against a native `make dev`
# process and a running container — same assertions, so "it worked locally"
# and "it works in the image" mean the same thing.
#
# Exits non-zero on the first failure. This is the definition of "satisfied";
# reading JSON and nodding is not.
set -uo pipefail

ENDPOINT="${ENDPOINT:-http://localhost:8080}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRACE_ID="5b8efff798038103d269b633813fc60c"

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

# --- probes ----------------------------------------------------------------
echo "probes"
assert "GET /healthz"          "200" "$(status GET /healthz)"
assert "GET /readyz"           "200" "$(status GET /readyz)"
assert "GET /metrics"          "200" "$(status GET /metrics)"
assert "/metrics is Prometheus text" "yes" \
  "$(curl -s "$ENDPOINT/metrics" | grep -q '^# TYPE telemetry_received_total counter' && echo yes || echo no)"

# --- notes CRUD ------------------------------------------------------------
echo "notes crud"
id=$(curl -s -X POST "$ENDPOINT/api/notes" -H 'content-type: application/json' \
     -d '{"title":"verify","body":"x"}' | jq_py 'd["id"]')
assert "POST /api/notes returns an id" "yes" "$([ -n "$id" ] && echo yes || echo no)"
assert "GET  /api/notes/{id}"   "200" "$(status GET "/api/notes/$id")"
assert "empty title rejected"   "400" "$(status POST /api/notes '{"title":"   "}')"
assert "DELETE /api/notes/{id}" "204" "$(status DELETE "/api/notes/$id")"
assert "deleted note is gone"   "404" "$(status GET "/api/notes/$id")"

# --- OTLP ingest -----------------------------------------------------------
#
# Assertions here are *invariants*, not deltas against a pre-count. An earlier
# version asserted `before + 4` and passed on a cold database, then failed on
# every re-run — because spans carry a uniqueness key and dedupe, while logs do
# not and accumulate. Both behaviours are correct; the assertion encoded a
# cold-start assumption. A check that only passes once is not a check.
echo "otlp ingest"
ENDPOINT="$ENDPOINT" "$HERE/testdata/send.sh" > /dev/null 2>&1
sleep 1

s=$(curl -s "$ENDPOINT/api/summary")
assert "spans present"    "yes" \
  "$(echo "$s" | jq_py '"yes" if d["stored"]["spans"] >= 4 else "no"')"
assert "2 services seen"  "checkout,payments" \
  "$(echo "$s" | jq_py '",".join(sorted(d["stored"]["services"]))')"

# The exponentialHistogram in the fixture is unsupported on purpose: it must be
# counted as skipped, never silently discarded.
assert "unsupported metric counted, not dropped silently" "yes" \
  "$(curl -s "$ENDPOINT/metrics" | awk '/^telemetry_skipped_total\{signal="metrics"\}/ {print ($2>0)?"yes":"no"}')"

# --- query -----------------------------------------------------------------
echo "query"
assert "logs filtered by severity" "1" \
  "$(curl -s "$ENDPOINT/api/logs?severity=error&limit=1" | jq_py 'd["count"]')"
# Logs have no uniqueness key, so re-delivery duplicates them by design — the
# count is a multiple of 3, not exactly 3.
assert "logs correlate to a trace" "yes" \
  "$(curl -s "$ENDPOINT/api/logs?trace_id=$TRACE_ID" \
     | jq_py '"yes" if d["count"] >= 3 and d["count"] % 3 == 0 else "no"')"
assert "attributes inflated to objects, not strings" "dict" \
  "$(curl -s "$ENDPOINT/api/logs?severity=error&limit=1" | jq_py 'type(d["logs"][0]["attributes"]).__name__')"
assert "trace list honours min_duration_ms" "0" \
  "$(curl -s "$ENDPOINT/api/traces?min_duration_ms=100000" | jq_py 'd["count"]')"
assert "unknown trace is 404" "404" "$(status GET /api/traces/deadbeef)"

# --- trace assembly --------------------------------------------------------
echo "trace assembly"
t=$(curl -s "$ENDPOINT/api/traces/$TRACE_ID")
assert "4 spans in the trace"   "4"     "$(echo "$t" | jq_py 'd["span_count"]')"
assert "single root"            "False" "$(echo "$t" | jq_py 'd["partial"]')"
assert "one error span"         "1"     "$(echo "$t" | jq_py 'd["error_count"]')"
assert "root has 2 children"    "2"     "$(echo "$t" | jq_py 'len(d["spans"][0]["children"])')"
assert "grandchild nested under charge_card" "SELECT payment_methods" \
  "$(echo "$t" | jq_py '[c for c in d["spans"][0]["children"] if c["name"]=="charge_card"][0]["children"][0]["name"]')"
assert "cross-service stitch"   "payments" \
  "$(echo "$t" | jq_py '[c for c in d["spans"][0]["children"] if c["name"]=="charge_card"][0]["service_name"]')"

# --- idempotency -----------------------------------------------------------
echo "idempotency"
n0=$(curl -s "$ENDPOINT/api/summary" | jq_py 'd["stored"]["spans"]')
ENDPOINT="$ENDPOINT" "$HERE/testdata/send.sh" > /dev/null 2>&1
sleep 1
n1=$(curl -s "$ENDPOINT/api/summary" | jq_py 'd["stored"]["spans"]')
assert "re-delivered spans deduped" "$n0" "$n1"
assert "dedupes are counted" "yes" \
  "$(curl -s "$ENDPOINT/metrics" | awk '/^telemetry_deduped_total\{signal="traces"\}/ {print ($2>0)?"yes":"no"}')"

# --- result ----------------------------------------------------------------
echo
if [ "$fail" -eq 0 ]; then
  printf '\033[32m%d passed, 0 failed\033[0m — ship it\n' "$pass"
  exit 0
else
  printf '\033[31m%d passed, %d FAILED\033[0m — do not build the image yet\n' "$pass" "$fail"
  exit 1
fi
