#!/usr/bin/env bash
#
# Check a list of HTTP endpoints in parallel and report which ones failed.
# Usage: ./parallel_health_check.sh -f hosts.txt [-t timeout_seconds] [-p parallelism]
#
# Demonstrates, in one small script, the "tricks" section of the doc this
# lives next to: getopts for real flag parsing, backgrounded jobs + wait
# for parallelism, process substitution to read a file without losing
# loop-local state, jq to parse each response, and trap on both EXIT and
# INT/TERM so a Ctrl+C mid-run still cleans up temp files.

set -uo pipefail   # no -e here on purpose: a single failed curl must not abort the whole batch

timeout=5
parallelism=8
hosts_file=""

usage() {
    echo "Usage: $0 -f hosts_file [-t timeout_seconds] [-p parallelism]" >&2
    exit 1
}

while getopts "f:t:p:h" opt; do
    case "$opt" in
        f) hosts_file="$OPTARG" ;;
        t) timeout="$OPTARG" ;;
        p) parallelism="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

[ -n "$hosts_file" ] || usage
[ -f "$hosts_file" ] || { echo "ERROR: hosts file not found: $hosts_file" >&2; exit 1; }

results_dir="$(mktemp -d)"

cleanup() {
    rm -rf "$results_dir"
}
trap cleanup EXIT
trap 'echo "interrupted, cleaning up" >&2; exit 130' INT
trap 'echo "terminated, cleaning up" >&2; exit 143' TERM

check_one() {
    local url="$1"
    local out_file="$2"
    local http_code
    # curl already writes 000 via -w on a connection/DNS failure and just
    # exits nonzero on top of it, so no `|| echo "000"` fallback is needed
    # here (adding one double-prints "000000" on that failure path).
    http_code="$(curl -s -o /dev/null -w '%{http_code}' --max-time "$timeout" "$url")"
    if [ "$http_code" = "200" ]; then
        echo "OK ${url} (${http_code})" > "$out_file"
    else
        echo "FAIL ${url} (${http_code})" > "$out_file"
    fi
}

# Launch checks in parallel, capped at $parallelism concurrent jobs.
job_count=0
i=0
while IFS= read -r url; do
    [ -n "$url" ] || continue                # skip blank lines
    i=$((i + 1))
    check_one "$url" "${results_dir}/${i}.result" &
    job_count=$((job_count + 1))
    if [ "$job_count" -ge "$parallelism" ]; then
        wait -n            # wait for just one job to finish before starting more
        job_count=$((job_count - 1))
    fi
done < <(grep -v '^\s*#' "$hosts_file")     # process substitution: keeps the loop in this shell, not a subshell

wait   # block until every remaining backgrounded check_one has finished

fail_count=0
for result_file in "${results_dir}"/*.result; do
    [ -e "$result_file" ] || continue   # nullglob-free guard: no results at all
    line="$(cat "$result_file")"
    echo "$line"
    [[ "$line" == FAIL* ]] && fail_count=$((fail_count + 1))
done

echo "---"
echo "checked ${i} host(s), ${fail_count} failed"

[ "$fail_count" -eq 0 ]   # script's own exit code: 0 only if nothing failed
