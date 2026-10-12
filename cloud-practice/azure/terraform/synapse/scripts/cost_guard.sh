#!/usr/bin/env bash
# Show anything in this project that can still bill, and pause the dedicated pool if it is running.
set -euo pipefail
cd "$(dirname "$0")/.."
RG=$(terraform output -raw resource_group); WS=$(terraform output -raw workspace_name)

echo "== Dedicated SQL pools (bill hourly while Online) =="
az synapse sql pool list -g "$RG" --workspace-name "$WS" --query "[].{name:name,sku:sku.name,status:status}" -o table || true
for p in $(az synapse sql pool list -g "$RG" --workspace-name "$WS" --query "[?status=='Online'].name" -o tsv); do
  echo "Pausing $p ..."; az synapse sql pool pause -g "$RG" --workspace-name "$WS" -n "$p"
done

echo "== Spark pools (bill only while a session is running; Spark apps listed below) =="
az synapse spark pool list -g "$RG" --workspace-name "$WS" --query "[].{name:name,nodes:nodeCount,autoPauseMin:autoPause.delayInMinutes}" -o table || true
az synapse spark job list --workspace-name "$WS" --spark-pool-name sparksmall --query "[?state=='running'||state=='starting'].{id:id,state:state}" -o table 2>/dev/null || true
