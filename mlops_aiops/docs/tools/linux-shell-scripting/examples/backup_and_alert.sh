#!/usr/bin/env bash
#
# Archive a directory, verify the archive, and exit non-zero on failure.
# Usage: ./backup_and_alert.sh <source-dir> <backup-dir>
#
# Demonstrates, in one small script, the shape most real housekeeping
# scripts share: strict mode, argument validation, functions, a loop,
# and an explicit exit code as the final verdict.

set -euo pipefail

log() {
    # timestamped log lines to stdout; errors go to stderr separately (see fail())
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

fail() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
    exit 1
}

usage() {
    echo "Usage: $0 <source-dir> <backup-dir>" >&2
    exit 1
}

[ "$#" -eq 2 ] || usage

source_dir="$1"
backup_dir="$2"

[ -d "$source_dir" ] || fail "source directory not found: $source_dir"
mkdir -p "$backup_dir"

timestamp="$(date +%Y%m%d_%H%M%S)"
archive_name="backup_${timestamp}.tar.gz"
archive_path="${backup_dir}/${archive_name}"

log "archiving ${source_dir} -> ${archive_path}"
tar -czf "$archive_path" -C "$(dirname "$source_dir")" "$(basename "$source_dir")"

[ -f "$archive_path" ] || fail "archive was not created"

archive_size="$(du -h "$archive_path" | cut -f1)"
log "archive created (${archive_size})"

log "verifying archive integrity"
if ! tar -tzf "$archive_path" > /dev/null; then
    fail "archive failed integrity check: $archive_path"
fi

log "pruning backups older than 7 days in ${backup_dir}"
old_count=0
while IFS= read -r old_backup; do
    log "removing old backup: $old_backup"
    rm -f "$old_backup"
    old_count=$((old_count + 1))
done < <(find "$backup_dir" -name "backup_*.tar.gz" -mtime +7)

log "pruned ${old_count} old backup(s)"
log "backup complete: ${archive_path}"
exit 0
