#!/usr/bin/env bash
set -Eeo pipefail

if [ -z "$(ls -A "$PGDATA" 2>/dev/null)" ]; then
    echo "PGDATA is empty, taking a base backup from primary..."
    until gosu postgres pg_basebackup -h primary -p 5432 -D "$PGDATA" -U replicator -Fp -Xs -P -R; do
        echo "primary not ready yet, retrying in 2s..."
        sleep 2
    done
    echo "base backup complete."
fi

exec docker-entrypoint.sh postgres
