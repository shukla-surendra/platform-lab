#!/usr/bin/env bash
# Removes everything from solution 1 (the whole solution2 namespace).
set -euo pipefail
cd "$(dirname "$0")"
NS=solution2
source ../lib.sh
need_cluster
kubectl delete namespace $NS --ignore-not-found --wait=false
echo "waiting for the namespace to disappear..."
for _ in $(seq 1 45); do
  kubectl get namespace $NS >/dev/null 2>&1 || { ok "clean: namespace $NS is gone"; exit 0; }
  sleep 3
done
bad "still terminating; check: kubectl get ns $NS"; exit 1
