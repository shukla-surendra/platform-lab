#!/usr/bin/env bash
# Runs once per `docker compose up`: data -> registry -> online store.
set -euo pipefail

echo "== 1/3 load demo data into Postgres (offline store)"
python /app/scripts/load_data.py

cd /app/feature_repo

echo "== 2/3 feast apply (register entities, feature views, feature services in the SQL registry)"
feast apply

echo "== 3/3 feast materialize (copy the latest offline values into Redis)"
END=$(date -u +"%Y-%m-%dT%H:%M:%S")
START=$(date -u -d "30 days ago" +"%Y-%m-%dT%H:%M:%S")
feast materialize "$START" "$END"

echo "== done: online store is populated; feature server can start"
