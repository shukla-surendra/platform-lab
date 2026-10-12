#!/usr/bin/env bash
# Generate sample data and upload it to the lake's "raw" filesystem.
# Usage: ./scripts/upload_data.sh      (run from the synapse/ directory after terraform apply)
set -euo pipefail
cd "$(dirname "$0")/.."

SA=$(terraform output -raw storage_account)
python3 scripts/generate_data.py

# --auth-mode login uses your Entra identity (needs Storage Blob Data Owner; Terraform grants it,
# but role assignments can take 1-5 minutes to propagate, so retry if you get 403).
az storage fs directory create -f raw -n sales     --account-name "$SA" --auth-mode login -o none
az storage fs directory create -f raw -n reference --account-name "$SA" --auth-mode login -o none
az storage fs directory create -f raw -n events    --account-name "$SA" --auth-mode login -o none

az storage blob upload-batch -d raw --destination-path sales -s data/sales --account-name "$SA" --auth-mode login --overwrite -o none
az storage fs file upload -f raw -p reference/customers.csv --source data/customers.csv --account-name "$SA" --auth-mode login --overwrite -o none
az storage fs file upload -f raw -p reference/products.csv  --source data/products.csv  --account-name "$SA" --auth-mode login --overwrite -o none
az storage fs file upload -f raw -p events/events.jsonl     --source data/events.jsonl  --account-name "$SA" --auth-mode login --overwrite -o none

echo "Uploaded. Listing raw/:"
az storage fs file list -f raw --account-name "$SA" --auth-mode login --recursive true --query "[].name" -o tsv
