#!/usr/bin/env bash
# Run the pipeline once, wait for it, and show the output file.
# Usage: ./scripts/run_pipeline.sh [fileName]     (default: orders.csv)
set -euo pipefail
cd "$(dirname "$0")/.."

FILE="${1:-orders.csv}"
RG=$(terraform output -raw resource_group_name)
ADF=$(terraform output -raw data_factory_name)
PL=$(terraform output -raw pipeline_name)
SA=$(terraform output -raw storage_account_name)

RUN_ID=$(az datafactory pipeline create-run -g "$RG" --factory-name "$ADF" \
  --name "$PL" --parameters "{\"fileName\": \"$FILE\"}" --query runId -o tsv)
echo "Started run $RUN_ID (file=$FILE)"

while true; do
  STATUS=$(az datafactory pipeline-run show -g "$RG" --factory-name "$ADF" \
    --run-id "$RUN_ID" --query status -o tsv)
  echo "  status: $STATUS"
  case "$STATUS" in
    Succeeded) break ;;
    Failed|Cancelled)
      az datafactory pipeline-run show -g "$RG" --factory-name "$ADF" --run-id "$RUN_ID" \
        --query message -o tsv
      exit 1 ;;
  esac
  sleep 10
done

echo "--- processed/$FILE ---"
az storage blob download --account-name "$SA" --container-name processed \
  --name "$FILE" --auth-mode key --file /dev/stdout --no-progress 2>/dev/null
