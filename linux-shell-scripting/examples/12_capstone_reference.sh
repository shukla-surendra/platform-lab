#!/usr/bin/env bash
#
# Reference solution for the capstone exercise in
# 12-worked-examples-and-real-world.md. Try writing your own version
# first — this is here to check your work against, not to copy from.
#
# Usage: ./12_capstone_reference.sh -d <directory> -a <age_in_days>

set -euo pipefail

usage() {
    echo "Usage: $0 -d directory -a age_in_days" >&2
    exit 1
}

dir=""
age=""

while getopts "d:a:h" opt; do
    case "$opt" in
        d) dir="$OPTARG" ;;
        a) age="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

[ -n "$dir" ] && [ -n "$age" ] || usage
[ -d "$dir" ] || { echo "ERROR: not a directory: $dir" >&2; exit 1; }

report_file="$(mktemp)"
trap 'rm -f "$report_file"' EXIT

log_file() {
    local path="$1"
    local size
    size=$(du -h "$path" | cut -f1)
    echo "$path  ($size)" >> "$report_file"
}

match_count=0
while IFS= read -r path; do
    log_file "$path"
    match_count=$((match_count + 1))
done < <(find "$dir" -type f -mtime "+$age")

if [ "$match_count" -eq 0 ]; then
    echo "ERROR: no files older than $age day(s) found in $dir" >&2
    exit 1
fi

echo "Found $match_count file(s) older than $age day(s):"
cat "$report_file"
