#!/usr/bin/env bash
#
# Demonstrates the scriptable half of 05-terminal-productivity.md: diff,
# comm, column, time, rsync, and symlinks. (history/!!/Ctrl+R/aliases/
# tmux are interactive-only and can't be meaningfully scripted — try
# those by hand in your terminal.)

set -uo pipefail

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

echo "=== diff ==="
printf 'a\nb\nc\n' > "$work_dir/f1"
printf 'a\nx\nc\n' > "$work_dir/f2"
diff -u "$work_dir/f1" "$work_dir/f2"

echo
echo "=== comm (needs sorted input) ==="
sort "$work_dir/f1" -o "$work_dir/f1.sorted"
sort "$work_dir/f2" -o "$work_dir/f2.sorted"
comm "$work_dir/f1.sorted" "$work_dir/f2.sorted"

echo
echo "=== column ==="
printf 'name\tport\nweb\t8080\napi\t9090\n' | column -t

echo
echo "=== time ==="
time sleep 1

echo
echo "=== rsync (local dirs, same idea works over ssh) ==="
mkdir -p "$work_dir/src" "$work_dir/dst"
echo "content" > "$work_dir/src/file.txt"
rsync -avz "$work_dir/src/" "$work_dir/dst/"
ls -la "$work_dir/dst"

echo
echo "=== symlink ==="
ln -s "$work_dir/dst" "$work_dir/current"
ls -la "$work_dir/current"
