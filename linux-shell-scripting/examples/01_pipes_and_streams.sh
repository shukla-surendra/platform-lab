#!/usr/bin/env bash
#
# Demonstrates the two ideas from 01-introduction-and-mental-model.md:
# every command is a process with an exit code and three streams
# (stdin/stdout/stderr), and you can rewire those streams.

set -uo pipefail

echo "=== 1. every command reports an exit code ==="
true
echo "exit code of 'true': $?"
false
echo "exit code of 'false': $?"

echo
echo "=== 2. stdout and stderr are separate streams ==="
out_file="$(mktemp)"
err_file="$(mktemp)"
{ echo "this is stdout"; echo "this is stderr" >&2; } 1>"$out_file" 2>"$err_file"
echo "captured stdout: $(cat "$out_file")"
echo "captured stderr: $(cat "$err_file")"
rm -f "$out_file" "$err_file"

echo
echo "=== 3. piping: one process's stdout becomes the next one's stdin ==="
printf 'error: disk full\ninfo: ok\nerror: timeout\n' | grep error | wc -l
