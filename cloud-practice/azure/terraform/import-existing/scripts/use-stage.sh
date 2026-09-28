#!/usr/bin/env bash
# Swap the *.tf for a given stage into tf/ (versions.tf and state stay put).
#   scripts/use-stage.sh 02-import | 03-modify
set -euo pipefail
cd "$(dirname "$0")/.."
stage="${1:?usage: $0 02-import|03-modify}"
[[ -d "stages/$stage" ]] || { echo "no such stage: $stage"; ls stages; exit 1; }

rm -f tf/main.tf tf/imports.tf
cp stages/"$stage"/*.tf tf/
echo "tf/ now uses stage $stage:"
ls tf/*.tf
