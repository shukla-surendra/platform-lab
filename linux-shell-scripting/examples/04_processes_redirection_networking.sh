#!/usr/bin/env bash
#
# Demonstrates 04-processes-redirection-networking.md: background jobs,
# redirection with tee, and archives. (curl/scp/ssh are skipped here to
# keep this script runnable offline — try those by hand against a real
# host.)

set -uo pipefail

echo "=== background jobs ==="
sleep 30 &
job_pid=$!
jobs
echo "started 'sleep 30' as PID $job_pid, killing it now"
kill "$job_pid" 2>/dev/null
wait "$job_pid" 2>/dev/null
echo "done"

echo
echo "=== redirection: tee writes to a file AND still prints ==="
out_file="$(mktemp)"
echo "hello" > "$out_file"
cat "$out_file" | tee -a "$out_file" >/dev/null
echo "file now contains:"
cat "$out_file"
rm -f "$out_file"

echo
echo "=== archives ==="
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT
mkdir -p "$work_dir/data"
echo "sample" > "$work_dir/data/file.txt"
tar -czvf "$work_dir/backup.tar.gz" -C "$work_dir" data
echo "created: $work_dir/backup.tar.gz"
du -sh "$work_dir/backup.tar.gz"
