#!/usr/bin/env bash
#
# Demonstrates 03-files-and-text-processing.md: generates a fake log
# file, then runs the grep/awk/sort/uniq pipeline questions from the doc
# against real data.
#
# Usage: ./03_text_processing_pipeline.sh [log_file]

set -euo pipefail

log_file="${1:-$HOME/practice/app.log}"
mkdir -p "$(dirname "$log_file")"

echo "Generating a fake log at $log_file ..."
: > "$log_file"
for i in $(seq 1 200); do
    ip="192.168.1.$((RANDOM % 20))"
    level=$([ $((RANDOM % 5)) -eq 0 ] && echo ERROR || echo INFO)
    echo "$(date +'%Y-%m-%d %H:%M:%S') $ip $level request handled" >> "$log_file"
done

echo
echo "=== top 5 IPs by request count ==="
awk '{print $3}' "$log_file" | sort | uniq -c | sort -rn | head -5

echo
echo "=== ERROR line count ==="
grep -c ERROR "$log_file"

echo
echo "=== error rate (%) ==="
total=$(wc -l < "$log_file")
errors=$(grep -c ERROR "$log_file")
echo "scale=2; ($errors / $total) * 100" | bc
